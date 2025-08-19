"""
Custom exceptions for Codex2API.

This module defines all custom exceptions used throughout the application,
following OpenAI API error format for consistency.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class Codex2APIError(Exception):
    """Base exception for all Codex2API errors."""
    
    def __init__(
        self,
        message: str,
        error_type: str = "codex2api_error",
        error_code: Optional[str] = None,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary format."""
        error_dict = {
            "message": self.message,
            "type": self.error_type,
        }
        
        if self.error_code:
            error_dict["code"] = self.error_code
        
        if self.details:
            error_dict.update(self.details)
        
        return {"error": error_dict}


class AuthenticationError(Codex2APIError):
    """Authentication related errors."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=message,
            error_type="authentication_error",
            error_code=error_code,
            status_code=401,
            details=details
        )


class AuthorizationError(Codex2APIError):
    """Authorization related errors."""
    
    def __init__(
        self,
        message: str = "Insufficient permissions",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=message,
            error_type="authorization_error",
            error_code=error_code,
            status_code=403,
            details=details
        )


class ValidationError(Codex2APIError):
    """Request validation errors."""
    
    def __init__(
        self,
        message: str = "Invalid request data",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=message,
            error_type="invalid_request_error",
            error_code=error_code,
            status_code=400,
            details=details
        )


class RateLimitError(Codex2APIError):
    """Rate limiting errors."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=message,
            error_type="rate_limit_exceeded",
            error_code=error_code,
            status_code=429,
            details=details
        )


class TokenError(Codex2APIError):
    """Token related errors."""
    
    def __init__(
        self,
        message: str = "Token error",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=message,
            error_type="token_error",
            error_code=error_code,
            status_code=401,
            details=details
        )


class TokenExpiredError(TokenError):
    """Token expired error."""
    
    def __init__(
        self,
        message: str = "Token has expired",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=message,
            error_code="token_expired",
            details=details
        )


class TokenRefreshError(TokenError):
    """Token refresh error."""
    
    def __init__(
        self,
        message: str = "Failed to refresh token",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=message,
            error_code="token_refresh_failed",
            details=details
        )


class APIError(Codex2APIError):
    """External API errors."""
    
    def __init__(
        self,
        message: str = "External API error",
        error_code: Optional[str] = None,
        status_code: int = 502,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=message,
            error_type="api_error",
            error_code=error_code,
            status_code=status_code,
            details=details
        )


class OpenAIError(APIError):
    """OpenAI API specific errors."""
    
    def __init__(
        self,
        message: str = "OpenAI API error",
        error_code: Optional[str] = None,
        status_code: int = 502,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details
        )


class ChatGPTError(APIError):
    """ChatGPT specific errors."""
    
    def __init__(
        self,
        message: str = "ChatGPT error",
        error_code: Optional[str] = None,
        status_code: int = 502,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details
        )


class ModelNotFoundError(Codex2APIError):
    """Model not found error."""
    
    def __init__(
        self,
        model_name: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        message = f"Model '{model_name}' not found"
        super().__init__(
            message=message,
            error_type="model_not_found",
            error_code="model_not_found",
            status_code=404,
            details=details
        )


class ConfigurationError(Codex2APIError):
    """Configuration related errors."""
    
    def __init__(
        self,
        message: str = "Configuration error",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=message,
            error_type="configuration_error",
            error_code=error_code,
            status_code=500,
            details=details
        )


class ServiceUnavailableError(Codex2APIError):
    """Service unavailable error."""
    
    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=message,
            error_type="service_unavailable",
            error_code=error_code,
            status_code=503,
            details=details
        )


class TimeoutError(Codex2APIError):
    """Request timeout error."""
    
    def __init__(
        self,
        message: str = "Request timeout",
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message=message,
            error_type="timeout_error",
            error_code=error_code,
            status_code=408,
            details=details
        )


# Error code mappings for common scenarios
ERROR_CODES = {
    # Authentication errors
    "invalid_token": "The provided token is invalid",
    "token_expired": "The token has expired",
    "token_refresh_failed": "Failed to refresh the token",
    "missing_token": "Authentication token is required",
    
    # Authorization errors
    "insufficient_permissions": "Insufficient permissions for this operation",
    "account_suspended": "Account has been suspended",
    
    # Validation errors
    "invalid_model": "The specified model is not valid",
    "invalid_parameters": "One or more parameters are invalid",
    "missing_required_field": "A required field is missing",
    
    # Rate limiting
    "rate_limit_exceeded": "Rate limit exceeded, please try again later",
    "quota_exceeded": "Usage quota has been exceeded",
    
    # API errors
    "upstream_error": "Error from upstream service",
    "service_unavailable": "Service is temporarily unavailable",
    "timeout": "Request timed out",
}


def get_error_message(error_code: str) -> str:
    """Get human-readable error message for error code."""
    return ERROR_CODES.get(error_code, "An unknown error occurred")
