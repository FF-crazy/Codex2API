"""
Authentication middleware for Codex2API.

This module provides FastAPI middleware for handling authentication,
session management, and request authorization.
"""

from __future__ import annotations

import time
from typing import Callable, Optional, Set

from fastapi import Request, Response, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

from ..core import (
    get_logger,
    AuthenticationError,
    AuthorizationError,
    TokenError,
    validate_bearer_token,
    generate_request_id,
    log_auth_event,
    log_security_event,
    SecurityContext,
)
from .token_manager import get_token_manager
from .session import get_session_manager, SessionData


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for handling authentication and session management."""
    
    def __init__(self, app, exclude_paths: Optional[Set[str]] = None):
        super().__init__(app)
        self.logger = get_logger(__name__)
        self.token_manager = get_token_manager()
        self.session_manager = get_session_manager()
        
        # Paths that don't require authentication
        self.exclude_paths = exclude_paths or {
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/auth/login",
            "/auth/callback",
            "/auth/status"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through authentication middleware."""
        start_time = time.time()
        request_id = generate_request_id()
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Get client info
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent")
        
        # Create security context
        security_context = SecurityContext(
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id
        )
        request.state.security_context = security_context
        
        try:
            # Check if path requires authentication
            if self._is_excluded_path(request.url.path):
                response = await call_next(request)
            else:
                # Authenticate request
                await self._authenticate_request(request)
                response = await call_next(request)
            
            # Add security headers
            self._add_security_headers(response)
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(
                "Authentication middleware error",
                request_id=request_id,
                path=request.url.path,
                error=str(e),
                exc_info=True
            )
            raise HTTPException(status_code=500, detail="Internal server error")
        
        finally:
            # Log request completion
            duration_ms = (time.time() - start_time) * 1000
            self.logger.info(
                "Request processed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
                authenticated=getattr(security_context, 'authenticated', False)
            )
    
    async def _authenticate_request(self, request: Request) -> None:
        """
        Authenticate the request.
        
        Args:
            request: FastAPI request object
            
        Raises:
            HTTPException: If authentication fails
        """
        security_context = request.state.security_context
        
        # Try session-based authentication first
        session_id = self._get_session_id(request)
        if session_id:
            session = await self._authenticate_with_session(request, session_id)
            if session:
                security_context.authenticate(
                    user_id=session.user_id,
                    permissions=session.permissions
                )
                request.state.session = session
                return
        
        # Try token-based authentication
        auth_header = request.headers.get("authorization")
        if auth_header:
            await self._authenticate_with_token(request, auth_header)
            return
        
        # No valid authentication found
        log_security_event(
            self.logger,
            "authentication_required",
            "medium",
            security_context.client_ip,
            details={"path": request.url.path}
        )
        
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    async def _authenticate_with_session(
        self,
        request: Request,
        session_id: str
    ) -> Optional[SessionData]:
        """
        Authenticate using session ID.
        
        Args:
            request: FastAPI request object
            session_id: Session identifier
            
        Returns:
            Session data if valid, None otherwise
        """
        try:
            security_context = request.state.security_context
            
            session = self.session_manager.validate_session(
                session_id=session_id,
                client_ip=security_context.client_ip
            )
            
            if session:
                log_auth_event(
                    self.logger,
                    "session_authentication_success",
                    user_id=session.user_id,
                    success=True,
                    details={"session_id": session_id}
                )
                return session
            else:
                log_auth_event(
                    self.logger,
                    "session_authentication_failed",
                    success=False,
                    details={"session_id": session_id}
                )
                return None
                
        except Exception as e:
            self.logger.error(
                "Session authentication error",
                session_id=session_id,
                error=str(e)
            )
            return None
    
    async def _authenticate_with_token(
        self,
        request: Request,
        auth_header: str
    ) -> None:
        """
        Authenticate using bearer token.
        
        Args:
            request: FastAPI request object
            auth_header: Authorization header value
            
        Raises:
            HTTPException: If token authentication fails
        """
        try:
            # Extract token
            token = validate_bearer_token(auth_header)
            
            # For now, we'll implement a simple token validation
            # In a real implementation, you'd validate against stored tokens
            # or decode JWT tokens
            
            # This is a placeholder - implement actual token validation
            user_id = await self._validate_api_token(token)
            if not user_id:
                raise AuthenticationError("Invalid token")
            
            # Authenticate security context
            security_context = request.state.security_context
            security_context.authenticate(user_id=user_id)
            
            log_auth_event(
                self.logger,
                "token_authentication_success",
                user_id=user_id,
                success=True
            )
            
        except (AuthenticationError, TokenError) as e:
            log_security_event(
                self.logger,
                "invalid_token_attempt",
                "medium",
                request.state.security_context.client_ip,
                details={"error": str(e)}
            )
            
            raise HTTPException(
                status_code=401,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    async def _validate_api_token(self, token: str) -> Optional[str]:
        """
        Validate API token and return user ID.
        
        Args:
            token: API token to validate
            
        Returns:
            User ID if token is valid, None otherwise
        """
        # This is a placeholder implementation
        # In a real system, you would:
        # 1. Check if token exists in database
        # 2. Validate token signature (if JWT)
        # 3. Check token expiration
        # 4. Return associated user ID
        
        # For now, accept any token that starts with "sk-"
        if token.startswith("sk-"):
            return "api_user"  # Placeholder user ID
        
        return None
    
    def _get_session_id(self, request: Request) -> Optional[str]:
        """
        Extract session ID from request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Session ID if found, None otherwise
        """
        # Try cookie first
        session_id = request.cookies.get("session_id")
        if session_id:
            return session_id
        
        # Try header
        session_id = request.headers.get("x-session-id")
        if session_id:
            return session_id
        
        return None
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client IP address
        """
        # Check for forwarded headers (reverse proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _is_excluded_path(self, path: str) -> bool:
        """
        Check if path is excluded from authentication.
        
        Args:
            path: Request path
            
        Returns:
            True if path is excluded
        """
        return path in self.exclude_paths or path.startswith("/static/")
    
    def _add_security_headers(self, response: Response) -> None:
        """
        Add security headers to response.
        
        Args:
            response: FastAPI response object
        """
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value


class RequireAuth:
    """Dependency for requiring authentication on specific endpoints."""
    
    def __init__(self, permissions: Optional[Set[str]] = None):
        self.permissions = permissions or set()
        self.logger = get_logger(__name__)
    
    async def __call__(self, request: Request) -> SecurityContext:
        """
        Validate authentication and permissions.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Security context
            
        Raises:
            HTTPException: If authentication or authorization fails
        """
        security_context = getattr(request.state, 'security_context', None)
        if not security_context:
            raise HTTPException(status_code=500, detail="Security context not found")
        
        if not security_context.authenticated:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Check permissions
        if self.permissions:
            missing_permissions = self.permissions - security_context.permissions
            if missing_permissions:
                log_security_event(
                    self.logger,
                    "insufficient_permissions",
                    "medium",
                    security_context.client_ip,
                    details={
                        "user_id": security_context.user_id,
                        "required": list(self.permissions),
                        "missing": list(missing_permissions)
                    }
                )
                
                raise HTTPException(
                    status_code=403,
                    detail=f"Missing permissions: {', '.join(missing_permissions)}"
                )
        
        return security_context


# Convenience instances
require_auth = RequireAuth()
require_admin = RequireAuth(permissions={"admin"})


# Bearer token security scheme for OpenAPI docs
bearer_scheme = HTTPBearer(auto_error=False)
