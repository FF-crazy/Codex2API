"""
Codex2API data models.

This module provides all Pydantic models for authentication, requests, and responses.
All models are compatible with the original ChatMock dataclass models while providing
enhanced validation and serialization capabilities.
"""

from __future__ import annotations

# Authentication models
from .auth import (
    TokenData,
    AuthBundle,
    PkceCodes,
    AuthStatus,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
)

# Request models
from .requests import (
    ChatMessage,
    ChatCompletionRequest,
    CompletionRequest,
)

# Response models
from .responses import (
    Usage,
    ToolCall,
    ChatCompletionMessage,
    ChatCompletionChoice,
    ChatCompletionResponse,
    ChatCompletionChunk,
    CompletionChoice,
    CompletionResponse,
    ModelInfo,
    ModelsResponse,
    ErrorResponse,
)

__all__ = [
    # Authentication models
    "TokenData",
    "AuthBundle",
    "PkceCodes",
    "AuthStatus",
    "LoginRequest",
    "LoginResponse",
    "RefreshTokenRequest",
    "RefreshTokenResponse",
    # Request models
    "ChatMessage",
    "ChatCompletionRequest",
    "CompletionRequest",
    # Response models
    "Usage",
    "ToolCall",
    "ChatCompletionMessage",
    "ChatCompletionChoice",
    "ChatCompletionResponse",
    "ChatCompletionChunk",
    "CompletionChoice",
    "CompletionResponse",
    "ModelInfo",
    "ModelsResponse",
    "ErrorResponse",
]
