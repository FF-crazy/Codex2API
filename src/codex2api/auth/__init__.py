"""
Authentication modules for Codex2API.

This package contains all authentication-related functionality including
OAuth flows, token management, session handling, and middleware.
"""

from __future__ import annotations

from .oauth import OAuthClient
from .token_manager import TokenManager, get_token_manager
from .session import SessionData, SessionManager, get_session_manager
from .middleware import (
    AuthenticationMiddleware,
    RequireAuth,
    require_auth,
    require_admin,
    bearer_scheme,
)

__all__ = [
    # OAuth
    "OAuthClient",
    # Token management
    "TokenManager",
    "get_token_manager",
    # Session management
    "SessionData",
    "SessionManager",
    "get_session_manager",
    # Middleware
    "AuthenticationMiddleware",
    "RequireAuth",
    "require_auth",
    "require_admin",
    "bearer_scheme",
]
