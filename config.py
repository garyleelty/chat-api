import os
import logging
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List, Dict, Any
from enum import Enum
import json


class Environment(str, Enum):
    """Environment types for configuration management."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"
    STAGING = "staging"


class LogFormat(str, Enum):
    """Logging format options."""
    SIMPLE = "simple"
    JSON = "json"
    STRUCTURED = "structured"


class BrowserConfig(BaseModel):
    """Browser-specific configuration."""
    BROWSER_TYPE: str = "chromium"  # chromium, firefox, webkit
    HEADLESS: bool = True
    SLOW_MO: int = 0  # Slow down operations for debugging
    TIMEOUT: int = 30000  # Default timeout in milliseconds
    VIEWPORT_WIDTH: int = 1920
    VIEWPORT_HEIGHT: int = 1080
    USER_AGENT: Optional[str] = None
    DEVICE_SCALE_FACTOR: float = 1.0
    IS_MOBILE: bool = False
    HAS_TOUCH: bool = False
    
    # Browser launch arguments
    EXTRA_ARGS: List[str] = Field(default_factory=list)
    
    @field_validator('BROWSER_TYPE')
    @classmethod
    def validate_browser_type(cls, v):
        allowed = ['chromium', 'firefox', 'webkit']
        if v not in allowed:
            raise ValueError(f'Browser type must be one of: {allowed}')
        return v
    
    @field_validator('TIMEOUT')
    @classmethod
    def validate_timeout(cls, v):
        if v < 1000 or v > 300000:
            raise ValueError('Timeout must be between 1000 and 300000 milliseconds')
        return v


class LoggingConfig(BaseModel):
    """Structured logging configuration."""
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: LogFormat = LogFormat.STRUCTURED
    LOG_FILE: Optional[str] = None
    LOG_ROTATION: str = "500 MB"
    LOG_RETENTION: str = "10 days"
    LOG_COMPRESSION: Optional[str] = "zip"
    LOG_SERIALIZE: bool = True
    LOG_INCLUDE_CONTEXT: bool = True
    
    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v):
        allowed = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed:
            raise ValueError(f'Log level must be one of: {allowed}')
        return v.upper()


class SessionConfig(BaseModel):
    """Session management configuration."""
    MAX_SESSIONS: int = 10
    SESSION_TIMEOUT: int = 3600  # 1 hour in seconds
    SESSION_CLEANUP_INTERVAL: int = 300  # 5 minutes
    SESSION_MAX_AGE: int = 7200  # 2 hours
    SESSION_POOL_SIZE: int = 5
    
    @field_validator('MAX_SESSIONS')
    @classmethod
    def validate_max_sessions(cls, v):
        if v < 1 or v > 50:
            raise ValueError('Max sessions must be between 1 and 50')
        return v
    
    @field_validator('SESSION_TIMEOUT')
    @classmethod
    def validate_session_timeout(cls, v):
        if v < 300 or v > 86400:
            raise ValueError('Session timeout must be between 300 and 86400 seconds')
        return v


class RetryConfig(BaseModel):
    """Retry mechanism configuration."""
    MAX_RETRIES: int = 3
    INITIAL_RETRY_DELAY: float = 1.0
    MAX_RETRY_DELAY: float = 60.0
    RETRY_BACKOFF_MULTIPLIER: float = 2.0
    RETRY_JITTER: bool = True
    RETRY_ON_EXCEPTIONS: List[str] = Field(default_factory=lambda: [
        "TimeoutError",
        "ConnectionError",
        "RuntimeError"
    ])
    
    @field_validator('MAX_RETRIES')
    @classmethod
    def validate_max_retries(cls, v):
        if v < 0 or v > 10:
            raise ValueError('Max retries must be between 0 and 10')
        return v


class HealthCheckConfig(BaseModel):
    """Health check configuration."""
    HEALTH_CHECK_INTERVAL: int = 60  # seconds
    HEALTH_CHECK_TIMEOUT: int = 30  # seconds
    HEALTH_CHECK_THRESHOLD: int = 3  # consecutive failures
    HEALTH_CHECK_ENABLED: bool = True
    HEALTH_CHECK_ENDPOINT: str = "/health"
    
    @field_validator('HEALTH_CHECK_INTERVAL')
    @classmethod
    def validate_health_check_interval(cls, v):
        if v < 10 or v > 3600:
            raise ValueError('Health check interval must be between 10 and 3600 seconds')
        return v


class Settings(BaseSettings):
    """Application settings and configuration with environment-specific overrides."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=True,
        extra="ignore"
    )
    
    # Environment
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    
    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Doubao Chat API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    RELOAD: bool = False
    
    # Doubao Configuration
    DOUBAO_URL: str = "https://www.doubao.com/chat/"
    DOUBAO_LOGIN_URL: Optional[str] = None
    
    # Authentication (if needed)
    DOUBAO_USERNAME: Optional[str] = None
    DOUBAO_PASSWORD: Optional[str] = None
    
    # API Key Authentication
    API_KEYS: List[str] = Field(default_factory=list)
    API_KEY_HEADER_NAME: str = "X-API-Key"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_REQUESTS_PER_DAY: int = 10000
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["*"])
    CORS_METHODS: List[str] = Field(default_factory=lambda: ["*"])
    CORS_HEADERS: List[str] = Field(default_factory=lambda: ["*"])
    CORS_CREDENTIALS: bool = True
    
    # Sub-configurations
    BROWSER: BrowserConfig = Field(default_factory=BrowserConfig)
    LOGGING: LoggingConfig = Field(default_factory=LoggingConfig)
    SESSION: SessionConfig = Field(default_factory=SessionConfig)
    RETRY: RetryConfig = Field(default_factory=RetryConfig)
    HEALTH_CHECK: HealthCheckConfig = Field(default_factory=HealthCheckConfig)
    
    # Request Validation
    MAX_MESSAGE_LENGTH: int = 4000
    MIN_MESSAGE_LENGTH: int = 1
    
    # Monitoring and Observability
    ENABLE_METRICS: bool = True
    METRICS_ENDPOINT: str = "/metrics"
    ENABLE_TRACING: bool = False
    TRACING_ENDPOINT: Optional[str] = None
    
    # Graceful Shutdown
    SHUTDOWN_TIMEOUT: int = 30  # seconds
    GRACEFUL_SHUTDOWN_ENABLED: bool = True
    
    # Configuration Management
    CONFIG_PATH: Optional[str] = None
    ENV_FILE: Optional[str] = None
    
    @model_validator(mode='before')
    @classmethod
    def validate_environment_specific_settings(cls, values):
        """Apply environment-specific configuration overrides."""
        env = values.get('ENVIRONMENT', Environment.DEVELOPMENT)
        
        # Environment-specific defaults
        env_defaults = {
            Environment.DEVELOPMENT: {
                'DEBUG': True,
                'RELOAD': True,
                'LOGGING': {
                    'LOG_LEVEL': 'DEBUG',
                    'LOG_FORMAT': 'structured'
                },
                'BROWSER': {
                    'HEADLESS': False,
                    'SLOW_MO': 100
                }
            },
            Environment.PRODUCTION: {
                'DEBUG': False,
                'RELOAD': False,
                'LOGGING': {
                    'LOG_LEVEL': 'INFO',
                    'LOG_FORMAT': 'json',
                    'LOG_SERIALIZE': True
                },
                'BROWSER': {
                    'HEADLESS': True,
                    'SLOW_MO': 0
                },
                'RATE_LIMIT_ENABLED': True,
                'ENABLE_METRICS': True
            },
            Environment.TESTING: {
                'DEBUG': True,
                'LOGGING': {
                    'LOG_LEVEL': 'DEBUG'
                },
                'BROWSER': {
                    'HEADLESS': True,
                    'TIMEOUT': 15000
                }
            },
            Environment.STAGING: {
                'DEBUG': False,
                'LOGGING': {
                    'LOG_LEVEL': 'INFO',
                    'LOG_FORMAT': 'structured'
                },
                'BROWSER': {
                    'HEADLESS': True
                }
            }
        }
        
        # Apply environment defaults if not explicitly set
        if env in env_defaults:
            env_config = env_defaults[env]
            for key, value in env_config.items():
                if key not in values or values[key] is None:
                    values[key] = value
        
        return values
    
    @field_validator('MAX_MESSAGE_LENGTH')
    @classmethod
    def validate_max_message_length(cls, v):
        if v < 1 or v > 10000:
            raise ValueError('Max message length must be between 1 and 10000')
        return v
    
    @field_validator('MIN_MESSAGE_LENGTH')
    @classmethod
    def validate_min_message_length(cls, v):
        if v < 1 or v > 100:
            raise ValueError('Min message length must be between 1 and 100')
        return v
    
    @field_validator('PORT')
    @classmethod
    def validate_port(cls, v):
        if v < 1 or v > 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v
    
    @field_validator('WORKERS')
    @classmethod
    def validate_workers(cls, v):
        if v < 1 or v > 50:
            raise ValueError('Workers must be between 1 and 50')
        return v
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get structured logging configuration."""
        config = {
            "level": self.LOGGING.LOG_LEVEL,
            "format": self.LOGGING.LOG_FORMAT.value,
            "serialize": self.LOGGING.LOG_SERIALIZE,
            "include_context": self.LOGGING.LOG_INCLUDE_CONTEXT,
        }
        
        if self.LOGGING.LOG_FILE:
            config.update({
                "rotation": self.LOGGING.LOG_ROTATION,
                "retention": self.LOGGING.LOG_RETENTION,
                "compression": self.LOGGING.LOG_COMPRESSION,
            })
        
        return config
    
    def get_browser_args(self) -> List[str]:
        """Get browser launch arguments based on configuration."""
        args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--disable-gpu",
            f"--window-size={self.BROWSER.VIEWPORT_WIDTH},{self.BROWSER.VIEWPORT_HEIGHT}",
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-features=IsolateOrigins",
            "--disable-site-isolation-trials"
        ]
        
        if self.DEBUG or self.ENVIRONMENT == Environment.DEVELOPMENT:
            args.append("--auto-open-devtools-for-tabs")
        
        # Add extra args from config
        args.extend(self.BROWSER.EXTRA_ARGS)
        
        return args
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == Environment.DEVELOPMENT
    
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.ENVIRONMENT == Environment.TESTING


def setup_logging(settings: Settings):
    """Setup structured logging based on configuration."""
    try:
        # Import structlog for structured logging
        import structlog
        
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer() if settings.LOGGING.LOG_FORMAT == LogFormat.JSON else
                structlog.dev.ConsoleRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
        # Configure standard logging
        logging.basicConfig(
            format="%(message)s",
            level=getattr(logging, settings.LOGGING.LOG_LEVEL),
            force=True
        )
        
    except ImportError:
        # Fallback to standard logging if structlog is not available
        logging.basicConfig(
            level=getattr(logging, settings.LOGGING.LOG_LEVEL),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            force=True
        )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured for environment: {settings.ENVIRONMENT.value}")
    logger.info(f"Log level: {settings.LOGGING.LOG_LEVEL}")
    logger.info(f"Log format: {settings.LOGGING.LOG_FORMAT.value}")


# Global settings instance
settings = Settings()

# Setup logging on import
setup_logging(settings)
