"""
Codex2API - OpenAI compatible API powered by your ChatGPT plan.

This package provides a modern FastAPI-based server that creates an OpenAI/Ollama 
compatible API, with requests fulfilled using your authenticated ChatGPT login.
"""

__version__ = "0.2.0"
__author__ = "Codex2API Contributors"
__email__ = "contact@codex2api.dev"

from .models import AuthBundle, PkceCodes, TokenData
from .server import create_app

__all__ = [
    "AuthBundle",
    "PkceCodes", 
    "TokenData",
    "create_app",
    "__version__",
]
