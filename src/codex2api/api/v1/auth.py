"""
Authentication API endpoints for Codex2API.

This module implements authentication-related endpoints including
OAuth login, callback handling, and session management.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from ...auth import (
    OAuthClient,
    get_token_manager,
    get_session_manager,
    require_auth,
)
from ...core import (
    get_logger,
    get_settings,
    AuthenticationError,
    TokenError,
    SecurityContext,
    log_auth_event,
    log_error,
)
from ...models import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    ErrorResponse,
)

# Create router
router = APIRouter(prefix="/auth", tags=["authentication"])
logger = get_logger(__name__)


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="Initiate OAuth login",
    description="Initiate OAuth login flow and return authorization URL.",
)
async def login(
    request: LoginRequest,
    http_request: Request,
) -> LoginResponse:
    """
    Initiate OAuth login flow.

    Returns an authorization URL that the client should redirect to
    for OAuth authentication with OpenAI.
    """
    try:
        # Get client info
        client_ip = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("user-agent")

        # Create OAuth client
        async with OAuthClient() as oauth_client:
            # Generate authorization URL
            auth_url, pkce_codes, state = oauth_client.generate_auth_url(
                no_browser=request.no_browser
            )

            # Store PKCE codes and state in session for later use
            # In a real implementation, you'd store this in a secure session store
            # For now, we'll return them to the client (not recommended for production)

            log_auth_event(
                logger,
                "login_initiated",
                success=True,
                details={
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                    "no_browser": request.no_browser,
                },
            )

            return LoginResponse(
                auth_url=auth_url,
                state=state,
                # In production, don't return these - store them server-side
                pkce_verifier=pkce_codes.code_verifier,
                pkce_challenge=pkce_codes.code_challenge,
            )

    except Exception as e:
        log_error(logger, e, context={"client_ip": client_ip})
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Login initiation failed: {str(e)}",
                    "type": "authentication_error",
                }
            },
        )


@router.get(
    "/callback",
    summary="OAuth callback",
    description="Handle OAuth callback from OpenAI authentication.",
)
async def oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    http_request: Request = None,
) -> RedirectResponse:
    """
    Handle OAuth callback.

    This endpoint receives the authorization code from OpenAI and exchanges
    it for access tokens, then creates a user session.
    """
    try:
        # Check for OAuth errors
        if error:
            log_auth_event(
                logger,
                "oauth_callback_error",
                success=False,
                details={"error": error, "error_description": error_description},
            )
            # Redirect to error page
            return RedirectResponse(
                url=f"/auth/error?error={error}&description={error_description or ''}",
                status_code=302,
            )

        if not code or not state:
            raise AuthenticationError("Missing authorization code or state")

        # Get client info
        client_ip = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("user-agent")

        # In a real implementation, you'd retrieve the stored PKCE codes and original state
        # For this demo, we'll create a simple error response
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": "OAuth callback handling requires session storage implementation",
                    "type": "implementation_error",
                    "code": "callback_not_implemented",
                }
            },
        )

    except AuthenticationError as e:
        log_error(logger, e)
        return RedirectResponse(
            url=f"/auth/error?error=authentication_failed&description={str(e)}", status_code=302
        )

    except Exception as e:
        log_error(logger, e)
        return RedirectResponse(
            url="/auth/error?error=internal_error&description=Authentication failed",
            status_code=302,
        )


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="Refresh access token",
    description="Refresh an expired access token using a refresh token.",
)
async def refresh_token(
    request: RefreshTokenRequest,
    http_request: Request,
) -> RefreshTokenResponse:
    """
    Refresh access token.

    Uses a refresh token to obtain a new access token when the current
    one has expired.
    """
    try:
        # Get client info
        client_ip = http_request.client.host if http_request.client else "unknown"

        # Create OAuth client
        async with OAuthClient() as oauth_client:
            # Refresh tokens
            new_token_data = await oauth_client.refresh_tokens(request.refresh_token)

            # Store new tokens
            token_manager = get_token_manager()
            auth_bundle = token_manager.store_tokens(new_token_data)

            log_auth_event(
                logger,
                "token_refreshed",
                user_id=new_token_data.account_id,
                success=True,
                details={"client_ip": client_ip},
            )

            return RefreshTokenResponse(
                access_token=new_token_data.access_token,
                refresh_token=new_token_data.refresh_token,
                expires_in=3600,  # Default expiration
                token_type="Bearer",
            )

    except TokenError as e:
        log_error(logger, e)
        raise HTTPException(status_code=401, detail=e.to_dict())

    except Exception as e:
        log_error(logger, e)
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": f"Token refresh failed: {str(e)}", "type": "token_error"}},
        )


@router.get(
    "/status",
    response_model=Dict[str, Any],
    summary="Get authentication status",
    description="Get current authentication status and user information.",
)
async def get_auth_status(
    security_context: SecurityContext = Depends(require_auth),
) -> Dict[str, Any]:
    """
    Get authentication status.

    Returns information about the current authentication state
    and user permissions.
    """
    try:
        return {
            "authenticated": security_context.authenticated,
            "user_id": security_context.user_id,
            "permissions": list(security_context.permissions),
            "client_ip": security_context.client_ip,
            "request_id": security_context.request_id,
        }

    except Exception as e:
        log_error(logger, e, context={"user_id": security_context.user_id})
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": "Failed to get authentication status",
                    "type": "internal_error",
                }
            },
        )


@router.post(
    "/logout",
    response_model=Dict[str, Any],
    summary="Logout user",
    description="Logout user and invalidate session.",
)
async def logout(
    security_context: SecurityContext = Depends(require_auth),
    http_request: Request = None,
) -> Dict[str, Any]:
    """
    Logout user.

    Invalidates the current session and cleans up authentication state.
    """
    try:
        # Get session manager
        session_manager = get_session_manager()

        # Get session ID from request
        session_id = None
        if http_request:
            session_id = http_request.cookies.get("session_id")
            if not session_id:
                session_id = http_request.headers.get("x-session-id")

        # Delete session if found
        if session_id:
            session_manager.delete_session(session_id)

        # Delete all user sessions
        if security_context.user_id:
            deleted_count = session_manager.delete_user_sessions(security_context.user_id)

            log_auth_event(
                logger,
                "user_logout",
                user_id=security_context.user_id,
                success=True,
                details={"sessions_deleted": deleted_count},
            )

        return {"success": True, "message": "Logged out successfully"}

    except Exception as e:
        log_error(logger, e, context={"user_id": security_context.user_id})
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": "Logout failed", "type": "internal_error"}},
        )


@router.get(
    "/sessions",
    response_model=Dict[str, Any],
    summary="List user sessions",
    description="List all active sessions for the current user.",
)
async def list_sessions(
    security_context: SecurityContext = Depends(require_auth),
) -> Dict[str, Any]:
    """
    List user sessions.

    Returns a list of all active sessions for the current user.
    """
    try:
        if not security_context.user_id:
            raise HTTPException(
                status_code=401,
                detail={"error": {"message": "User ID required", "type": "authentication_error"}},
            )

        session_manager = get_session_manager()
        sessions = session_manager.get_user_sessions(security_context.user_id)

        # Convert sessions to response format
        session_list = []
        for session in sessions:
            session_list.append(
                {
                    "session_id": session.session_id,
                    "created_at": session.created_at.isoformat(),
                    "last_accessed": session.last_accessed.isoformat(),
                    "expires_at": session.expires_at.isoformat(),
                    "client_ip": session.client_ip,
                    "user_agent": session.user_agent,
                    "permissions": list(session.permissions),
                }
            )

        return {"object": "list", "data": session_list, "total": len(session_list)}

    except Exception as e:
        log_error(logger, e, context={"user_id": security_context.user_id})
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": "Failed to list sessions", "type": "internal_error"}},
        )
