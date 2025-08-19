"""
Logging configuration for Codex2API.

This module sets up structured logging using structlog with support for
both JSON and human-readable formats.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from structlog.types import FilteringBoundLogger

from .config import LoggingConfig, get_settings


def setup_logging(config: Optional[LoggingConfig] = None) -> None:
    """
    Setup application logging configuration.
    
    Args:
        config: Logging configuration. If None, uses settings from environment.
    """
    if config is None:
        config = get_settings().logging
    
    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, config.level),
        format="%(message)s",
        handlers=_get_handlers(config)
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _add_request_id,
            _filter_sensitive_data,
            structlog.processors.JSONRenderer() if config.format == "json" 
            else structlog.dev.ConsoleRenderer(colors=True)
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, config.level)
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _get_handlers(config: LoggingConfig) -> list[logging.Handler]:
    """Get logging handlers based on configuration."""
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, config.level))
    handlers.append(console_handler)
    
    # File handler (if configured)
    if config.file_path:
        file_path = Path(config.file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=file_path,
            maxBytes=config.max_file_size,
            backupCount=config.backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(getattr(logging, config.level))
        handlers.append(file_handler)
    
    return handlers


def _add_request_id(
    logger: FilteringBoundLogger, 
    method_name: str, 
    event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Add request ID to log entries if available."""
    # This will be populated by middleware
    request_id = structlog.contextvars.get_contextvars().get("request_id")
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def _filter_sensitive_data(
    logger: FilteringBoundLogger, 
    method_name: str, 
    event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Filter sensitive data from log entries."""
    sensitive_keys = {
        "password", "token", "api_key", "secret", "authorization",
        "access_token", "refresh_token", "id_token", "client_secret"
    }
    
    def _filter_dict(data: Any) -> Any:
        if isinstance(data, dict):
            return {
                key: "[REDACTED]" if key.lower() in sensitive_keys 
                else _filter_dict(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [_filter_dict(item) for item in data]
        elif isinstance(data, str) and len(data) > 50:
            # Truncate very long strings that might contain tokens
            for sensitive_key in sensitive_keys:
                if sensitive_key in data.lower():
                    return "[REDACTED]"
        return data
    
    return _filter_dict(event_dict)


def get_logger(name: str = __name__) -> FilteringBoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name, typically __name__ of the calling module.
        
    Returns:
        Configured structlog logger instance.
    """
    return structlog.get_logger(name)


def log_request_start(
    logger: FilteringBoundLogger,
    method: str,
    path: str,
    client_ip: str,
    user_agent: Optional[str] = None,
    request_id: Optional[str] = None
) -> None:
    """Log the start of an HTTP request."""
    logger.info(
        "Request started",
        method=method,
        path=path,
        client_ip=client_ip,
        user_agent=user_agent,
        request_id=request_id
    )


def log_request_end(
    logger: FilteringBoundLogger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    request_id: Optional[str] = None
) -> None:
    """Log the end of an HTTP request."""
    logger.info(
        "Request completed",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        request_id=request_id
    )


def log_auth_event(
    logger: FilteringBoundLogger,
    event_type: str,
    user_id: Optional[str] = None,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Log authentication events."""
    logger.info(
        "Authentication event",
        event_type=event_type,
        user_id=user_id,
        success=success,
        **(details or {})
    )


def log_api_call(
    logger: FilteringBoundLogger,
    service: str,
    endpoint: str,
    method: str,
    status_code: int,
    duration_ms: float,
    request_size: Optional[int] = None,
    response_size: Optional[int] = None
) -> None:
    """Log external API calls."""
    logger.info(
        "External API call",
        service=service,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        duration_ms=duration_ms,
        request_size=request_size,
        response_size=response_size
    )


def log_error(
    logger: FilteringBoundLogger,
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> None:
    """Log errors with context."""
    logger.error(
        "Error occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        user_id=user_id,
        request_id=request_id,
        **(context or {}),
        exc_info=True
    )


def log_performance_metric(
    logger: FilteringBoundLogger,
    metric_name: str,
    value: float,
    unit: str = "ms",
    tags: Optional[Dict[str, str]] = None
) -> None:
    """Log performance metrics."""
    logger.info(
        "Performance metric",
        metric_name=metric_name,
        value=value,
        unit=unit,
        **(tags or {})
    )


def log_security_event(
    logger: FilteringBoundLogger,
    event_type: str,
    severity: str,
    client_ip: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Log security-related events."""
    logger.warning(
        "Security event",
        event_type=event_type,
        severity=severity,
        client_ip=client_ip,
        **(details or {})
    )


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes."""
    
    @property
    def logger(self) -> FilteringBoundLogger:
        """Get logger instance for this class."""
        return get_logger(self.__class__.__module__ + "." + self.__class__.__name__)


# Context managers for request logging
class RequestLoggingContext:
    """Context manager for request logging."""
    
    def __init__(
        self,
        logger: FilteringBoundLogger,
        method: str,
        path: str,
        client_ip: str,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        self.logger = logger
        self.method = method
        self.path = path
        self.client_ip = client_ip
        self.user_agent = user_agent
        self.request_id = request_id
        self.start_time: Optional[float] = None
    
    def __enter__(self) -> RequestLoggingContext:
        import time
        self.start_time = time.time()
        log_request_start(
            self.logger,
            self.method,
            self.path,
            self.client_ip,
            self.user_agent,
            self.request_id
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.start_time is not None:
            import time
            duration_ms = (time.time() - self.start_time) * 1000
            status_code = 500 if exc_type else 200
            log_request_end(
                self.logger,
                self.method,
                self.path,
                status_code,
                duration_ms,
                self.request_id
            )


# Initialize logging on module import
setup_logging()
