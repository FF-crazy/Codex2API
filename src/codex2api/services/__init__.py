"""
Service modules for Codex2API.

This package contains all business logic services including ChatGPT client,
OpenAI proxy, model management, and conversation handling.
"""

from __future__ import annotations

from .chatgpt_client import ChatGPTClient
from .openai_proxy import OpenAIProxyService, get_openai_proxy
from .model_manager import (
    ModelCapabilities,
    ModelMetadata,
    ModelManager,
    get_model_manager,
)

__all__ = [
    # ChatGPT client
    "ChatGPTClient",
    # OpenAI proxy
    "OpenAIProxyService",
    "get_openai_proxy",
    # Model management
    "ModelCapabilities",
    "ModelMetadata",
    "ModelManager",
    "get_model_manager",
]
