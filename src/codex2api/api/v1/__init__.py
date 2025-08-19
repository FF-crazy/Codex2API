"""
API v1 endpoints for Codex2API.

This package contains all v1 API endpoints including chat completions,
text completions, models, and authentication.
"""

from __future__ import annotations

from fastapi import APIRouter

from . import auth, chat, completions, models

# Create main v1 router
router = APIRouter(prefix="/v1")

# Include sub-routers
router.include_router(chat.router)
router.include_router(completions.router)
router.include_router(models.router)
router.include_router(auth.router)

__all__ = ["router"]
