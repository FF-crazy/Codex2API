"""
Core modules for Codex2API.

This package contains the core infrastructure components including
configuration, exceptions, logging, and security utilities.
"""

from __future__ import annotations

from .config import Settings, get_settings, reload_settings
from .exceptions import (
    Codex2APIError,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    RateLimitError,
    TokenError,
    TokenExpiredError,
    TokenRefreshError,
    APIError,
    OpenAIError,
    ChatGPTError,
    ModelNotFoundError,
    ConfigurationError,
    ServiceUnavailableError,
    TimeoutError,
    get_error_message,
)
from .logging import (
    get_logger,
    setup_logging,
    log_request_start,
    log_request_end,
    log_auth_event,
    log_api_call,
    log_error,
    log_performance_metric,
    log_security_event,
    LoggerMixin,
    RequestLoggingContext,
)
from .security import (
    generate_pkce_codes,
    verify_pkce_challenge,
    generate_state,
    generate_nonce,
    generate_session_id,
    generate_request_id,
    hash_token,
    verify_token_hash,
    is_token_expired,
    validate_bearer_token,
    sanitize_user_input,
    get_security_headers,
    mask_sensitive_data,
    validate_ip_address,
    is_safe_redirect_url,
    rate_limit_key,
    generate_api_key,
    SecurityContext,
)

__all__ = [
    # Configuration
    "Settings",
    "get_settings",
    "reload_settings",
    # Exceptions
    "Codex2APIError",
    "AuthenticationError",
    "AuthorizationError",
    "ValidationError",
    "RateLimitError",
    "TokenError",
    "TokenExpiredError",
    "TokenRefreshError",
    "APIError",
    "OpenAIError",
    "ChatGPTError",
    "ModelNotFoundError",
    "ConfigurationError",
    "ServiceUnavailableError",
    "TimeoutError",
    "get_error_message",
    # Logging
    "get_logger",
    "setup_logging",
    "log_request_start",
    "log_request_end",
    "log_auth_event",
    "log_api_call",
    "log_error",
    "log_performance_metric",
    "log_security_event",
    "LoggerMixin",
    "RequestLoggingContext",
    # Security
    "generate_pkce_codes",
    "verify_pkce_challenge",
    "generate_state",
    "generate_nonce",
    "generate_session_id",
    "generate_request_id",
    "hash_token",
    "verify_token_hash",
    "is_token_expired",
    "validate_bearer_token",
    "sanitize_user_input",
    "get_security_headers",
    "mask_sensitive_data",
    "validate_ip_address",
    "is_safe_redirect_url",
    "rate_limit_key",
    "generate_api_key",
    "SecurityContext",
]
