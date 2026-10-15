import time
import logging
import uuid
import contextvars
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from collections import defaultdict
import os
import structlog

from config import settings

logger = structlog.get_logger(__name__)

# Request ID context for distributed tracing
request_id_context = contextvars.ContextVar("request_id", default=None)


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        self.requests_per_minute: Dict[str, list] = defaultdict(list)
        self.requests_per_day: Dict[str, int] = defaultdict(int)
        self.cleanup_interval = 60  # Cleanup every minute
        self.last_cleanup = time.time()
    
    def _cleanup_old_requests(self):
        """Remove old requests from tracking."""
        current_time = time.time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        minute_ago = current_time - 60
        self.requests_per_minute = defaultdict(
            list,
            {key: [req_time for req_time in req_times if req_time > minute_ago]
             for key, req_times in self.requests_per_minute.items()}
        )
        self.last_cleanup = current_time
    
    def check_rate_limit(self, client_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if client has exceeded rate limits.
        
        Returns:
            tuple[bool, Optional[str]]: (is_allowed, error_message)
        """
        if not settings.RATE_LIMIT_ENABLED:
            return True, None
        
        self._cleanup_old_requests()
        current_time = time.time()
        
        # Check per-minute limit
        minute_requests = self.requests_per_minute[client_id]
        if len(minute_requests) >= settings.RATE_LIMIT_REQUESTS_PER_MINUTE:
            return False, f"Rate limit exceeded: {settings.RATE_LIMIT_REQUESTS_PER_MINUTE} requests per minute"
        
        # Check per-day limit
        day_requests = self.requests_per_day[client_id]
        if day_requests >= settings.RATE_LIMIT_REQUESTS_PER_DAY:
            return False, f"Rate limit exceeded: {settings.RATE_LIMIT_REQUESTS_PER_DAY} requests per day"
        
        # Record the request
        minute_requests.append(current_time)
        self.requests_per_day[client_id] += 1
        
        return True, None


class APIKeyValidator:
    """API key validation utility."""
    
    def __init__(self):
        self.api_keys = set(settings.API_KEYS)
    
    def is_valid_api_key(self, api_key: str) -> bool:
        """Check if the provided API key is valid."""
        if not settings.API_KEYS:
            # If no API keys configured, allow all requests (for development)
            return True
        return api_key in self.api_keys


# Global instances
rate_limiter = RateLimiter()
api_key_validator = APIKeyValidator()


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for API key authentication."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip authentication for health check and root endpoints
        if request.url.path in ["/", "/health", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Get API key from header (support both X-API-Key and Authorization: Bearer)
        api_key = request.headers.get(settings.API_KEY_HEADER_NAME)
        
        if not api_key:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                api_key = auth_header[7:]
        
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "error": "API key is required",
                    "detail": f"Please provide an API key in the '{settings.API_KEY_HEADER_NAME}' header or 'Authorization: Bearer <api_key>' header"
                }
            )
        
        if not api_key_validator.is_valid_api_key(api_key):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "success": False,
                    "error": "Invalid API key",
                    "detail": "The provided API key is not valid"
                }
            )
        
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health check and root endpoints
        if request.url.path in ["/", "/health", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Get client identifier (API key or IP address)
        api_key = request.headers.get(settings.API_KEY_HEADER_NAME)
        client_id = api_key or request.client.host if request.client else "unknown"
        
        is_allowed, error_message = rate_limiter.check_rate_limit(client_id)
        
        if not is_allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "error": "Rate limit exceeded",
                    "detail": error_message
                },
                headers={"Retry-After": "60"}
            )
        
        response = await call_next(request)
        
        # Add rate limit headers
        minute_requests = len(rate_limiter.requests_per_minute[client_id])
        day_requests = rate_limiter.requests_per_day[client_id]
        
        response.headers["X-RateLimit-Remaining-Minute"] = str(
            max(0, settings.RATE_LIMIT_REQUESTS_PER_MINUTE - minute_requests)
        )
        response.headers["X-RateLimit-Remaining-Day"] = str(
            max(0, settings.RATE_LIMIT_REQUESTS_PER_DAY - day_requests)
        )
        response.headers["X-RateLimit-Limit-Minute"] = str(settings.RATE_LIMIT_REQUESTS_PER_MINUTE)
        response.headers["X-RateLimit-Limit-Day"] = str(settings.RATE_LIMIT_REQUESTS_PER_DAY)
        
        return response


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Middleware for request tracing and correlation IDs."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate or get request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request_id_context.set(request_id)
        
        # Add request ID to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request logging."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        request_id = request_id_context.get()
        
        # Extract client information
        client_host = request.client.host if request.client else "unknown"
        client_port = request.client.port if request.client else None
        user_agent = request.headers.get('user-agent', 'unknown')
        
        # Log request with structured data
        logger.info(
            "Request received",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_host=client_host,
            client_port=client_port,
            user_agent=user_agent,
            headers={k: v for k, v in request.headers.items() if k.lower() not in ['authorization', 'cookie']}
        )
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log response with structured data
            logger.info(
                "Response sent",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
                response_headers=dict(response.headers),
                client_host=client_host
            )
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            
            # Log error with structured data
            logger.error(
                "Request failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error=str(e),
                error_type=type(e).__name__,
                process_time_ms=round(process_time * 1000, 2),
                client_host=client_host,
                exc_info=True
            )
            raise


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting metrics."""
    
    def __init__(self, app):
        super().__init__(app)
        self.request_count = 0
        self.error_count = 0
        self.total_processing_time = 0.0
    
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        self.request_count += 1
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            self.total_processing_time += process_time
            
            # Add metrics to response headers
            response.headers["X-Request-Count"] = str(self.request_count)
            response.headers["X-Processing-Time"] = str(round(process_time * 1000, 2))
            
            return response
            
        except Exception:
            self.error_count += 1
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response


def setup_middleware(app: FastAPI):
    """Setup all middleware for the application."""
    
    # Add request tracing middleware first (for correlation IDs)
    app.add_middleware(RequestTracingMiddleware)
    
    # Add security headers middleware
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Add authentication middleware
    app.add_middleware(AuthenticationMiddleware)
    
    # Add rate limiting middleware
    app.add_middleware(RateLimitMiddleware)
    
    # Add metrics middleware
    app.add_middleware(MetricsMiddleware)
    
    # Add request logging middleware (should be last to capture all processing)
    app.add_middleware(RequestLoggingMiddleware)