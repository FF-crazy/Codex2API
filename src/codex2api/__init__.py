"""
Codex2API - Modern OpenAI compatible API powered by ChatGPT.

This package provides a complete OpenAI-compatible API implementation
that proxies requests to ChatGPT's internal API while maintaining
full compatibility with OpenAI client libraries.
"""

from __future__ import annotations

__version__ = "0.2.0"
__author__ = "Codex2API Contributors"
__email__ = "contact@codex2api.dev"
__license__ = "MIT"
__description__ = "Modern OpenAI compatible API powered by ChatGPT"

# Core exports
from .core import get_settings, get_logger
from .main import create_app

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__license__",
    "__description__",
    "get_settings",
    "get_logger",
    "create_app",
]
