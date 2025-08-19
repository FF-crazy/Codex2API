"""
Main FastAPI application for Codex2API.

This module creates and configures the FastAPI application with all
middleware, routes, and error handlers.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .api import v1_router
from .auth import AuthenticationMiddleware
from .core import (
    get_logger,
    get_settings,
    setup_logging,
    Codex2APIError,
    log_error,
    log_request_start,
    log_request_end,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger = get_logger(__name__)
    settings = get_settings()
    
    logger.info(
        "Starting Codex2API",
        version=settings.app_version,
        environment=settings.environment
    )
    
    # Initialize logging
    setup_logging()
    
    # Cleanup expired sessions and tokens on startup
    try:
        from .auth import get_session_manager, get_token_manager
        
        session_manager = get_session_manager()
        token_manager = get_token_manager()
        
        expired_sessions = session_manager.cleanup_expired_sessions()
        expired_tokens = token_manager.cleanup_expired_tokens()
        
        logger.info(
            "Cleanup completed",
            expired_sessions=expired_sessions,
            expired_tokens=expired_tokens
        )
    except Exception as e:
        logger.warning("Cleanup failed", error=str(e))
    
    yield
    
    # Shutdown
    logger.info("Shutting down Codex2API")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.server.cors_origins,
        allow_credentials=True,
        allow_methods=settings.server.cors_methods,
        allow_headers=settings.server.cors_headers,
    )
    
    # Add authentication middleware
    app.add_middleware(
        AuthenticationMiddleware,
        exclude_paths={
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/v1/auth/login",
            "/v1/auth/callback",
        }
    )
    
    # Add request logging middleware
    app.add_middleware(RequestLoggingMiddleware)
    
    # Include API routers
    app.include_router(v1_router)
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": settings.app_version,
            "timestamp": time.time()
        }
    
    # Add error handlers
    @app.exception_handler(Codex2APIError)
    async def codex2api_error_handler(request: Request, exc: Codex2APIError):
        """Handle Codex2API errors."""
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict()
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": exc.detail,
                    "type": "http_error"
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger = get_logger(__name__)
        log_error(
            logger,
            exc,
            context={
                "method": request.method,
                "url": str(request.url),
                "client": request.client.host if request.client else "unknown"
            }
        )
        
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": "Internal server error",
                    "type": "internal_error"
                }
            }
        )
    
    return app


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests."""
    
    def __init__(self, app):
        super().__init__(app)
        self.logger = get_logger(__name__)
    
    async def dispatch(self, request: Request, call_next):
        """Process request with logging."""
        start_time = time.time()
        
        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent")
        request_id = getattr(request.state, 'request_id', 'unknown')
        
        # Log request start
        log_request_start(
            self.logger,
            method=request.method,
            path=request.url.path,
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id
        )
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            self.logger.error(
                "Request processing failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                request_id=request_id
            )
            status_code = 500
            raise
        
        # Log request end
        duration_ms = (time.time() - start_time) * 1000
        log_request_end(
            self.logger,
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            duration_ms=duration_ms,
            request_id=request_id
        )
        
        return response


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "codex2api.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
        workers=settings.server.workers if not settings.server.reload else 1,
        log_level=settings.logging.level.lower(),
        access_log=False,  # We handle logging ourselves
    )
