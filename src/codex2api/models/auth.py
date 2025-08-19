"""
Authentication related Pydantic models for Codex2API.

This module contains all authentication-related data models,
upgraded from dataclass to Pydantic v2 for better validation and serialization.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class TokenData(BaseModel):
    """
    OAuth token data containing all authentication tokens.

    Compatible with the original dataclass TokenData from ChatMock.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    id_token: str = Field(..., description="OpenAI ID token for user identification", min_length=1)
    access_token: str = Field(..., description="Access token for API authentication", min_length=1)
    refresh_token: str = Field(..., description="Refresh token for token renewal", min_length=1)
    account_id: str = Field(..., description="ChatGPT account identifier", min_length=1)


class AuthBundle(BaseModel):
    """
    Complete authentication bundle containing tokens and metadata.

    Compatible with the original dataclass AuthBundle from ChatMock.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    api_key: Optional[str] = Field(
        None, description="Optional OpenAI API key obtained through token exchange"
    )
    token_data: TokenData = Field(..., description="OAuth token data")
    last_refresh: str = Field(..., description="ISO timestamp of last token refresh", min_length=1)


class PkceCodes(BaseModel):
    """
    PKCE (Proof Key for Code Exchange) codes for OAuth security.

    Compatible with the original dataclass PkceCodes from ChatMock.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    code_verifier: str = Field(
        ..., description="PKCE code verifier (random string)", min_length=43, max_length=128
    )
    code_challenge: str = Field(
        ...,
        description="PKCE code challenge (SHA256 hash of verifier)",
        min_length=43,
        max_length=128,
    )


class AuthStatus(BaseModel):
    """
    Authentication status information for API responses.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    authenticated: bool = Field(..., description="Whether user is currently authenticated")
    email: Optional[str] = Field(None, description="User email address if available")
    plan: Optional[str] = Field(None, description="ChatGPT plan type (Plus, Pro, etc.)")
    account_id: Optional[str] = Field(None, description="ChatGPT account identifier")
    last_refresh: Optional[str] = Field(None, description="ISO timestamp of last token refresh")


class LoginRequest(BaseModel):
    """
    Request model for initiating OAuth login flow.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    no_browser: bool = Field(False, description="Whether to skip automatic browser opening")


class LoginResponse(BaseModel):
    """
    Response model for OAuth login initiation.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    auth_url: str = Field(
        ..., description="OAuth authorization URL for user to visit", min_length=1
    )
    message: str = Field(..., description="Human-readable instruction message", min_length=1)
    expires_in: int = Field(300, description="Seconds until the auth URL expires", gt=0)


class RefreshTokenRequest(BaseModel):
    """
    Request model for token refresh operation.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    force: bool = Field(False, description="Whether to force refresh even if token is still valid")


class RefreshTokenResponse(BaseModel):
    """
    Response model for token refresh operation.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    success: bool = Field(..., description="Whether the refresh operation succeeded")
    message: str = Field(..., description="Human-readable status message", min_length=1)
    last_refresh: Optional[str] = Field(None, description="ISO timestamp of the refresh operation")
