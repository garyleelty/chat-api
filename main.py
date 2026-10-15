import logging
import uvicorn
import time
import signal
import sys
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
import asyncio
from contextlib import asynccontextmanager
import uuid
import contextvars
from loguru import logger
from config import settings
from doubao_automation import DoubaoAutomation, create_doubao_automation, AutomationError, AutomationErrorType
from middleware import setup_middleware

# Request ID context for tracing
request_id_context = contextvars.ContextVar("request_id", default=None)

# Global automation instance
automation_instance: Optional[DoubaoAutomation] = None
automation_lock = asyncio.Lock()

# Graceful shutdown flag
shutdown_event = asyncio.Event()

# Health check background task
health_check_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application with enhanced startup/shutdown."""
    # Startup
    logger.info("Starting Doubao Chat API...")
    logger.info(f"Environment: {settings.ENVIRONMENT.value}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Log level: {settings.LOGGING.LOG_LEVEL}")
    
    global automation_instance, health_check_task
    
    # Setup signal handlers for graceful shutdown
    setup_signal_handlers()
    
    try:
        # Initialize automation with retry logic
        automation_instance = await create_doubao_automation(max_retries=settings.RETRY.MAX_RETRIES)
        
        # Perform health check
        health_status = await automation_instance.health_check()
        if health_status["healthy"]:
            logger.info("Successfully initialized Doubao automation")
            logger.info(f"Health status: {health_status}")
        else:
            logger.warning(f"Automation initialized but health check failed: {health_status}")
            
    except Exception as e:
        logger.error(f"Failed to initialize Doubao automation: {str(e)}", exc_info=True)
        automation_instance = None
    
    # Start health check background task if enabled
    if settings.HEALTH_CHECK.HEALTH_CHECK_ENABLED and automation_instance:
        health_check_task = asyncio.create_task(health_check_loop())
        logger.info("Health check loop started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Doubao Chat API...")
    
    # Cancel health check task
    if health_check_task:
        health_check_task.cancel()
        try:
            await health_check_task
        except asyncio.CancelledError:
            pass
        logger.info("Health check loop stopped")
    
    # Graceful shutdown with timeout
    if automation_instance:
        try:
            # Set shutdown timeout
            shutdown_timeout = settings.SHUTDOWN_TIMEOUT
            
            # Create shutdown task
            shutdown_task = asyncio.create_task(automation_instance.close())
            
            # Wait for shutdown with timeout
            done, pending = await asyncio.wait(
                [shutdown_task],
                timeout=shutdown_timeout
            )
            
            if pending:
                logger.warning(f"Shutdown timed out after {shutdown_timeout}s, forcing cleanup")
                for task in pending:
                    task.cancel()
            
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}", exc_info=True)
    
    logger.info("Shutdown complete")


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    def handle_signal(signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        shutdown_event.set()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, handle_signal)


async def health_check_loop():
    """Background health check loop."""
    while not shutdown_event.is_set():
        try:
            if automation_instance:
                health_status = await automation_instance.health_check()
                
                if not health_status["healthy"]:
                    logger.warning(f"Health check failed: {health_status}")
                    
                    # Attempt recovery if unhealthy
                    if settings.HEALTH_CHECK.HEALTH_CHECK_ENABLED:
                        logger.info("Attempting recovery from unhealthy state...")
                        recovery_success = await automation_instance.recover_from_failure()
                        
                        if recovery_success:
                            logger.info("Recovery successful")
                        else:
                            logger.error("Recovery failed")
                
                # Log health status periodically
                if health_status["healthy"]:
                    logger.debug(f"Health check passed: {health_status}")
                
        except Exception as e:
            logger.error(f"Error in health check loop: {str(e)}", exc_info=True)
        
        # Wait for next health check
        try:
            await asyncio.wait_for(
                shutdown_event.wait(),
                timeout=settings.HEALTH_CHECK.HEALTH_CHECK_INTERVAL
            )
        except asyncio.TimeoutError:
            continue


# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

# Setup additional middleware
setup_middleware(app)


# Pydantic models
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=settings.MIN_MESSAGE_LENGTH, max_length=settings.MAX_MESSAGE_LENGTH)
    clear_history: bool = False
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        if len(v.strip()) < settings.MIN_MESSAGE_LENGTH:
            raise ValueError(f'Message must be at least {settings.MIN_MESSAGE_LENGTH} characters')
        if len(v) > settings.MAX_MESSAGE_LENGTH:
            raise ValueError(f'Message must not exceed {settings.MAX_MESSAGE_LENGTH} characters')
        return v.strip()


class HealthDetailResponse(BaseModel):
    """Detailed health check response."""
    healthy: bool
    status: str
    initialized: bool
    session_age: int
    last_activity: int
    browser_connected: bool
    page_ready: bool
    retry_count: int
    errors: List[str]
    uptime_seconds: int
    memory_usage: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    code: str
    message: str
    detail: Optional[str] = None


class MetadataResponse(BaseModel):
    timestamp: datetime
    response_time_ms: int
    api_version: str
    request_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: Optional[str]
    success: bool
    error: Optional[ErrorResponse] = None
    metadata: MetadataResponse


class ConversationHistoryResponse(BaseModel):
    messages: List[str]
    success: bool
    error: Optional[ErrorResponse] = None
    metadata: MetadataResponse


class StatusResponse(BaseModel):
    status: str
    initialized: bool
    doubao_url: str
    success: bool = True
    metadata: Optional[MetadataResponse] = None


class ClearConversationResponse(BaseModel):
    success: bool
    message: str
    error: Optional[ErrorResponse] = None
    metadata: MetadataResponse


# API Routes
@app.get("/", response_model=StatusResponse)
async def root(request: Request):
    """Root endpoint to check API status."""
    start_time = time.time()
    
    response = StatusResponse(
        status="Doubao Chat API is running",
        initialized=automation_instance is not None and automation_instance.is_initialized,
        doubao_url=settings.DOUBAO_URL,
        metadata=MetadataResponse(
            timestamp=datetime.now(),
            response_time_ms=int((time.time() - start_time) * 1000),
            api_version=settings.VERSION,
            request_id=request.headers.get("X-Request-ID")
        )
    )
    
    return response


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, http_request: Request):
    """Send a message to Doubao and get response with enhanced error handling."""
    start_time = time.time()
    request_id = http_request.headers.get("X-Request-ID") or str(uuid.uuid4())
    
    # Set request ID in context
    request_id_context.set(request_id)
    
    # Log request
    logger.info(
        f"Chat request received",
        extra={
            "request_id": request_id,
            "message_length": len(request.message),
            "clear_history": request.clear_history
        }
    )
    
    # Check if automation is initialized
    if not automation_instance or not automation_instance.is_initialized:
        error_response = ErrorResponse(
            code="SERVICE_UNAVAILABLE",
            message="Service not available",
            detail="Doubao automation not initialized or unhealthy"
        )
        logger.warning("Service unavailable: automation not initialized")
        return ChatResponse(
            response=None,
            success=False,
            error=error_response,
            metadata=MetadataResponse(
                timestamp=datetime.now(timezone.utc),
                response_time_ms=int((time.time() - start_time) * 1000),
                api_version=settings.VERSION,
                request_id=request_id
            )
        )
    
    async with automation_lock:
        try:
            # Perform health check before processing
            health_status = await automation_instance.health_check()
            if not health_status["healthy"]:
                logger.warning(f"Automation unhealthy before chat: {health_status}")
                
                # Attempt recovery
                recovery_success = await automation_instance.recover_from_failure()
                if not recovery_success:
                    error_response = ErrorResponse(
                        code="SERVICE_UNAVAILABLE",
                        message="Service temporarily unavailable",
                        detail="Automation is unhealthy and recovery failed"
                    )
                    return ChatResponse(
                        response=None,
                        success=False,
                        error=error_response,
                        metadata=MetadataResponse(
                            timestamp=datetime.now(timezone.utc),
                            response_time_ms=int((time.time() - start_time) * 1000),
                            api_version=settings.VERSION,
                            request_id=request_id
                        )
                    )
            
            # Clear conversation if requested
            if request.clear_history:
                success = await automation_instance.clear_conversation()
                if not success:
                    logger.warning("Failed to clear conversation history")
                    error_response = ErrorResponse(
                        code="CLEAR_HISTORY_FAILED",
                        message="Failed to clear conversation history",
                        detail="The system was unable to clear the conversation history"
                    )
                    return ChatResponse(
                        response=None,
                        success=False,
                        error=error_response,
                        metadata=MetadataResponse(
                            timestamp=datetime.now(timezone.utc),
                            response_time_ms=int((time.time() - start_time) * 1000),
                            api_version=settings.VERSION,
                            request_id=request_id
                        )
                    )
            
            # Send message and get response with timeout
            try:
                response = await asyncio.wait_for(
                    automation_instance.send_message(request.message),
                    timeout=settings.BROWSER.TIMEOUT / 1000  # Convert to seconds
                )
                
                if response is None:
                    error_response = ErrorResponse(
                        code="NO_RESPONSE",
                        message="Failed to get response",
                        detail="Failed to get response from Doubao after all retries"
                    )
                    logger.warning("No response received from Doubao")
                    return ChatResponse(
                        response=None,
                        success=False,
                        error=error_response,
                        metadata=MetadataResponse(
                            timestamp=datetime.now(timezone.utc),
                            response_time_ms=int((time.time() - start_time) * 1000),
                            api_version=settings.VERSION,
                            request_id=request_id
                        )
                    )
                
                # Log successful response
                logger.info(
                    f"Chat response generated successfully",
                    extra={
                        "request_id": request_id,
                        "response_length": len(response),
                        "processing_time_ms": int((time.time() - start_time) * 1000)
                    }
                )
                
                return ChatResponse(
                    response=response,
                    success=True,
                    error=None,
                    metadata=MetadataResponse(
                        timestamp=datetime.now(timezone.utc),
                        response_time_ms=int((time.time() - start_time) * 1000),
                        api_version=settings.VERSION,
                        request_id=request_id
                    )
                )
                
            except asyncio.TimeoutError:
                logger.error(f"Chat request timeout after {settings.BROWSER.TIMEOUT}ms")
                error_response = ErrorResponse(
                    code="TIMEOUT",
                    message="Request timeout",
                    detail=f"Request exceeded maximum processing time of {settings.BROWSER.TIMEOUT}ms"
                )
                return ChatResponse(
                    response=None,
                    success=False,
                    error=error_response,
                    metadata=MetadataResponse(
                        timestamp=datetime.now(timezone.utc),
                        response_time_ms=int((time.time() - start_time) * 1000),
                        api_version=settings.VERSION,
                        request_id=request_id
                    )
                )
            
        except AutomationError as e:
            logger.error(
                f"Automation error in chat endpoint: {str(e)}",
                extra={
                    "request_id": request_id,
                    "error_type": e.error_type.value
                },
                exc_info=True
            )
            
            # Map automation error types to HTTP error codes
            error_code_map = {
                AutomationErrorType.INITIALIZATION_FAILED: "SERVICE_UNAVAILABLE",
                AutomationErrorType.BROWSER_CRASH: "SERVICE_UNAVAILABLE",
                AutomationErrorType.TIMEOUT_ERROR: "TIMEOUT",
                AutomationErrorType.ELEMENT_NOT_FOUND: "BAD_REQUEST",
                AutomationErrorType.NETWORK_ERROR: "SERVICE_UNAVAILABLE",
                AutomationErrorType.SESSION_EXPIRED: "UNAUTHORIZED",
                AutomationErrorType.UNKNOWN_ERROR: "INTERNAL_ERROR"
            }
            
            error_response = ErrorResponse(
                code=error_code_map.get(e.error_type, "INTERNAL_ERROR"),
                message=e.message,
                detail=e.detail
            )
            
            return ChatResponse(
                response=None,
                success=False,
                error=error_response,
                metadata=MetadataResponse(
                    timestamp=datetime.now(timezone.utc),
                    response_time_ms=int((time.time() - start_time) * 1000),
                    api_version=settings.VERSION,
                    request_id=request_id
                )
            )
            
        except Exception as e:
            logger.error(
                f"Unexpected error in chat endpoint: {str(e)}",
                extra={"request_id": request_id},
                exc_info=True
            )
            error_response = ErrorResponse(
                code="INTERNAL_ERROR",
                message="Internal server error",
                detail=str(e)
            )
            return ChatResponse(
                response=None,
                success=False,
                error=error_response,
                metadata=MetadataResponse(
                    timestamp=datetime.now(timezone.utc),
                    response_time_ms=int((time.time() - start_time) * 1000),
                    api_version=settings.VERSION,
                    request_id=request_id
                )
            )


class OpenAIChatMessage(BaseModel):
    role: str = "user"
    content: str

class OpenAIChatRequest(BaseModel):
    model: str = "doubao"
    messages: List[OpenAIChatMessage]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False

class OpenAIChatChoice(BaseModel):
    index: int = 0
    message: OpenAIChatMessage
    finish_reason: str = "stop"

class OpenAIChatUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

class OpenAIChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str = "doubao"
    choices: List[OpenAIChatChoice]
    usage: OpenAIChatUsage

@app.post("/v1/chat/completions", response_model=OpenAIChatResponse)
async def openai_chat_completions(request: OpenAIChatRequest, http_request: Request):
    """OpenAI compatible chat completions endpoint."""
    start_time = time.time()
    request_id = http_request.headers.get("X-Request-ID") or str(uuid.uuid4())
    
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages cannot be empty")
    
    last_message = request.messages[-1].content
    
    logger.info(
        f"OpenAI compatible chat request received",
        extra={
            "request_id": request_id,
            "model": request.model,
            "message_count": len(request.messages),
            "last_message_length": len(last_message)
        }
    )
    
    if not automation_instance or not automation_instance.is_initialized:
        raise HTTPException(status_code=503, detail="Service unavailable: automation not initialized")
    
    try:
        response = await asyncio.wait_for(
            automation_instance.send_message(last_message),
            timeout=90
        )
        
        logger.info(f"OpenAI compatible chat response generated successfully")
        
        return OpenAIChatResponse(
            id=f"chatcmpl-{request_id[:8]}",
            created=int(time.time()),
            model=request.model,
            choices=[
                OpenAIChatChoice(
                    index=0,
                    message=OpenAIChatMessage(role="assistant", content=response),
                    finish_reason="stop"
                )
            ],
            usage=OpenAIChatUsage(
                prompt_tokens=len(last_message),
                completion_tokens=len(response) if response else 0,
                total_tokens=len(last_message) + (len(response) if response else 0)
            )
        )
        
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Request timeout")
    except Exception as e:
        logger.error(f"Error in OpenAI compatible chat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history", response_model=ConversationHistoryResponse)
async def get_history(request: Request):
    """Get conversation history with enhanced error handling."""
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    
    logger.info(f"History request received", extra={"request_id": request_id})
    
    if not automation_instance or not automation_instance.is_initialized:
        error_response = ErrorResponse(
            code="SERVICE_UNAVAILABLE",
            message="Service not available",
            detail="Doubao automation not initialized"
        )
        return ConversationHistoryResponse(
            messages=[],
            success=False,
            error=error_response,
            metadata=MetadataResponse(
                timestamp=datetime.now(timezone.utc),
                response_time_ms=int((time.time() - start_time) * 1000),
                api_version=settings.VERSION,
                request_id=request_id
            )
        )
    
    async with automation_lock:
        try:
            # Check health before operation
            health_status = await automation_instance.health_check()
            if not health_status["healthy"]:
                logger.warning(f"Automation unhealthy before history: {health_status}")
                raise AutomationError(
                    error_type=AutomationErrorType.SESSION_EXPIRED,
                    message="Automation is unhealthy"
                )
            
            history = await automation_instance.get_conversation_history()
            
            logger.info(
                f"History retrieved successfully",
                extra={
                    "request_id": request_id,
                    "message_count": len(history)
                }
            )
            
            return ConversationHistoryResponse(
                messages=history,
                success=True,
                error=None,
                metadata=MetadataResponse(
                    timestamp=datetime.now(timezone.utc),
                    response_time_ms=int((time.time() - start_time) * 1000),
                    api_version=settings.VERSION,
                    request_id=request_id
                )
            )
            
        except AutomationError as e:
            logger.error(
                f"Automation error getting history: {str(e)}",
                extra={"request_id": request_id},
                exc_info=True
            )
            error_response = ErrorResponse(
                code="INTERNAL_ERROR",
                message=e.message,
                detail=e.detail
            )
            return ConversationHistoryResponse(
                messages=[],
                success=False,
                error=error_response,
                metadata=MetadataResponse(
                    timestamp=datetime.now(timezone.utc),
                    response_time_ms=int((time.time() - start_time) * 1000),
                    api_version=settings.VERSION,
                    request_id=request_id
                )
            )
            
        except Exception as e:
            logger.error(
                f"Unexpected error getting history: {str(e)}",
                extra={"request_id": request_id},
                exc_info=True
            )
            error_response = ErrorResponse(
                code="INTERNAL_ERROR",
                message="Internal server error",
                detail=str(e)
            )
            return ConversationHistoryResponse(
                messages=[],
                success=False,
                error=error_response,
                metadata=MetadataResponse(
                    timestamp=datetime.now(timezone.utc),
                    response_time_ms=int((time.time() - start_time) * 1000),
                    api_version=settings.VERSION,
                    request_id=request_id
                )
            )


@app.post("/clear", response_model=ClearConversationResponse)
async def clear_conversation(request: Request):
    """Clear the current conversation with enhanced error handling."""
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    
    logger.info(f"Clear conversation request received", extra={"request_id": request_id})
    
    if not automation_instance or not automation_instance.is_initialized:
        error_response = ErrorResponse(
            code="SERVICE_UNAVAILABLE",
            message="Service not available",
            detail="Doubao automation not initialized"
        )
        return ClearConversationResponse(
            success=False,
            message="Service not available",
            error=error_response,
            metadata=MetadataResponse(
                timestamp=datetime.now(timezone.utc),
                response_time_ms=int((time.time() - start_time) * 1000),
                api_version=settings.VERSION,
                request_id=request_id
            )
        )
    
    async with automation_lock:
        try:
            # Check health before operation
            health_status = await automation_instance.health_check()
            if not health_status["healthy"]:
                logger.warning(f"Automation unhealthy before clear: {health_status}")
                raise AutomationError(
                    error_type=AutomationErrorType.SESSION_EXPIRED,
                    message="Automation is unhealthy"
                )
            
            success = await automation_instance.clear_conversation()
            
            if success:
                logger.info("Conversation cleared successfully", extra={"request_id": request_id})
            else:
                logger.warning("Failed to clear conversation", extra={"request_id": request_id})
            
            return ClearConversationResponse(
                success=success,
                message="Conversation cleared successfully" if success else "Failed to clear conversation",
                error=None,
                metadata=MetadataResponse(
                    timestamp=datetime.now(timezone.utc),
                    response_time_ms=int((time.time() - start_time) * 1000),
                    api_version=settings.VERSION,
                    request_id=request_id
                )
            )
            
        except AutomationError as e:
            logger.error(
                f"Automation error clearing conversation: {str(e)}",
                extra={"request_id": request_id},
                exc_info=True
            )
            error_response = ErrorResponse(
                code="INTERNAL_ERROR",
                message=e.message,
                detail=e.detail
            )
            return ClearConversationResponse(
                success=False,
                message="Failed to clear conversation",
                error=error_response,
                metadata=MetadataResponse(
                    timestamp=datetime.now(timezone.utc),
                    response_time_ms=int((time.time() - start_time) * 1000),
                    api_version=settings.VERSION,
                    request_id=request_id
                )
            )
            
        except Exception as e:
            logger.error(
                f"Unexpected error clearing conversation: {str(e)}",
                extra={"request_id": request_id},
                exc_info=True
            )
            error_response = ErrorResponse(
                code="INTERNAL_ERROR",
                message="Internal server error",
                detail=str(e)
            )
            return ClearConversationResponse(
                success=False,
                message="Failed to clear conversation",
                error=error_response,
                metadata=MetadataResponse(
                    timestamp=datetime.now(timezone.utc),
                    response_time_ms=int((time.time() - start_time) * 1000),
                    api_version=settings.VERSION,
                    request_id=request_id
                )
            )


@app.get("/health", response_model=HealthDetailResponse)
async def health_check(request: Request):
    """Enhanced health check endpoint with detailed status reporting."""
    start_time = time.time()
    
    health_status = {
        "healthy": False,
        "status": "unhealthy",
        "initialized": False,
        "session_age": 0,
        "last_activity": 0,
        "browser_connected": False,
        "page_ready": False,
        "retry_count": 0,
        "errors": [],
        "uptime_seconds": 0,
        "memory_usage": None,
        "metrics": None
    }
    
    try:
        if automation_instance:
            # Get detailed health status from automation instance
            automation_health = await automation_instance.health_check()
            health_status.update(automation_health)
            
            # Calculate uptime
            if automation_instance.session_start_time:
                health_status["uptime_seconds"] = int(time.time() - automation_instance.session_start_time)
            
            # Get system metrics if available
            try:
                import psutil
                process = psutil.Process()
                health_status["memory_usage"] = {
                    "rss_mb": process.memory_info().rss / 1024 / 1024,
                    "vms_mb": process.memory_info().vms / 1024 / 1024,
                    "percent": process.memory_percent()
                }
                health_status["metrics"] = {
                    "cpu_percent": process.cpu_percent(),
                    "num_threads": process.num_threads(),
                    "open_files": len(process.open_files())
                }
            except ImportError:
                pass  # psutil not available, skip metrics
        
        # Determine overall status
        health_status["status"] = "healthy" if health_status["healthy"] else "unhealthy"
        
        # Log health check result
        log_level = logging.INFO if health_status["healthy"] else logging.WARNING
        logger.log(log_level, f"Health check result: {health_status['status']}")
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}", exc_info=True)
        health_status["errors"].append(f"Health check error: {str(e)}")
        health_status["status"] = "error"
    
    return health_status


@app.get("/health/simple")
async def health_check_simple(request: Request):
    """Simple health check endpoint for load balancers."""
    start_time = time.time()
    
    is_initialized = automation_instance is not None and automation_instance.is_initialized
    status = "healthy" if is_initialized else "unhealthy"
    
    return {
        "status": status,
        "initialized": is_initialized,
        "version": settings.VERSION,
        "success": True,
        "metadata": {
            "timestamp": datetime.now(timezone.utc),
            "response_time_ms": int((time.time() - start_time) * 1000),
            "api_version": settings.VERSION,
            "request_id": request.headers.get("X-Request-ID")
        }
    }


if __name__ == "__main__":
    """Run the application."""
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS,
        reload=settings.DEBUG
    )
