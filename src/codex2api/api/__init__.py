"""
API modules for Codex2API.

This package contains all API endpoints and routing logic.
"""

from __future__ import annotations

from .v1 import router as v1_router

__all__ = ["v1_router"]
