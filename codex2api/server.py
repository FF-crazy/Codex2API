"""
FastAPI server for Codex2API.

This module provides the main FastAPI application with OpenAI-compatible endpoints.
"""

import json
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from .request import ChatGPTRequestHandler

# Load environment variables from .env file
load_dotenv()

# Security
security = HTTPBearer()


def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify API key from Authorization header."""
    expected_key = os.getenv("KEY", "sk-test")

    if not credentials:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    # Extract the key from "Bearer sk-xxx" format
    provided_key = credentials.credentials

    if provided_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return provided_key


def load_models_from_file() -> List[Dict[str, Any]]:
    """Load models from models.json file."""
    models_paths = [
        "models.json",  # Current directory
        os.path.join(os.path.dirname(__file__), "..", "models.json"),  # Parent directory
    ]

    for path in models_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                models = data.get("models", [])
                # Convert to OpenAI API format
                return [
                    {
                        "id": model.get("id", model.get("name", "unknown")),
                        "object": "model",
                        "owned_by": "openai",
                    }
                    for model in models
                ]
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"Warning: Failed to read models file {path}: {e}")
            continue

    # Fallback to default models if file not found
    return [
        {"id": "gpt-5", "object": "model", "owned_by": "openai"},
        {"id": "gpt-4o", "object": "model", "owned_by": "openai"},
        {"id": "gpt-4", "object": "model", "owned_by": "openai"},
        {"id": "gpt-3.5-turbo", "object": "model", "owned_by": "openai"},
    ]


# Request/Response Models
class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = None
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=1.0, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    n: Optional[int] = Field(default=1, ge=1, le=128)
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = Field(default=None, ge=1)
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    parallel_tool_calls: Optional[bool] = True
    reasoning: Optional[Dict[str, Any]] = None


class CompletionRequest(BaseModel):
    model: str
    prompt: Union[str, List[str]]
    suffix: Optional[str] = None
    max_tokens: Optional[int] = Field(default=16, ge=1)
    temperature: Optional[float] = Field(default=1.0, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    n: Optional[int] = Field(default=1, ge=1, le=128)
    stream: Optional[bool] = False
    logprobs: Optional[int] = Field(default=None, ge=0, le=5)
    echo: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    best_of: Optional[int] = Field(default=1, ge=1, le=20)
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    reasoning: Optional[Dict[str, Any]] = None


# Global request handler
request_handler: Optional[ChatGPTRequestHandler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    global request_handler
    request_handler = ChatGPTRequestHandler(verbose=True)
    yield
    if request_handler:
        await request_handler.close()


def create_app(
    cors_origins: Optional[List[str]] = None,
    reasoning_effort: Optional[str] = None,
    reasoning_summary: Optional[bool] = None,
    reasoning_compat: Optional[str] = None,
) -> FastAPI:
    """Create and configure FastAPI application."""

    # Use environment variables with fallbacks
    if cors_origins is None:
        cors_origins = ["*"]
    if reasoning_effort is None:
        reasoning_effort = os.getenv("REASONING_EFFORT", "medium")
    if reasoning_summary is None:
        reasoning_summary = os.getenv("REASONING_SUMMARY", "true").lower() == "true"
    if reasoning_compat is None:
        reasoning_compat = os.getenv("REASONING_COMPAT", "think-tags")

    app = FastAPI(
        title="Codex2API",
        description="OpenAI compatible API powered by your ChatGPT plan",
        version="0.2.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Store configuration
    app.state.reasoning_effort = reasoning_effort
    app.state.reasoning_summary = reasoning_summary
    app.state.reasoning_compat = reasoning_compat

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {"message": "Codex2API - OpenAI compatible API powered by your ChatGPT plan"}

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy", "timestamp": int(time.time())}

    @app.get("/v1/models")
    async def list_models():
        """List available models from models.json file."""
        models = load_models_from_file()
        return {
            "object": "list",
            "data": models,
        }

    @app.post("/v1/chat/completions")
    async def chat_completions(
        request_data: ChatCompletionRequest, api_key: str = Depends(verify_api_key)
    ):
        """Handle chat completion requests."""
        if not request_handler:
            raise HTTPException(status_code=500, detail="Request handler not initialized")

        try:
            # Convert messages to dict format
            messages = [msg.model_dump() for msg in request_data.messages]

            upstream, response_data = await request_handler.chat_completion(
                model=request_data.model,
                messages=messages,
                stream=request_data.stream or False,
                tools=request_data.tools,
                tool_choice=request_data.tool_choice,
                parallel_tool_calls=request_data.parallel_tool_calls or False,
                reasoning_overrides=request_data.reasoning,
            )

            if request_data.stream:
                # Return streaming response
                if upstream is None:
                    raise HTTPException(status_code=500, detail="Failed to get streaming response")
                return StreamingResponse(
                    request_handler.stream_chat_completion(
                        upstream,
                        request_handler._normalize_model_name(request_data.model),
                        reasoning_compat=app.state.reasoning_compat,
                    ),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                    },
                )
            else:
                # Return non-streaming response
                if response_data is None:
                    raise HTTPException(status_code=500, detail="Failed to get response data")
                return JSONResponse(content=response_data)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    @app.post("/v1/completions")
    async def completions(request_data: CompletionRequest, api_key: str = Depends(verify_api_key)):
        """Handle text completion requests."""
        if not request_handler:
            raise HTTPException(status_code=500, detail="Request handler not initialized")

        try:
            # Handle prompt format
            prompt = request_data.prompt
            if isinstance(prompt, list):
                prompt = "".join([p if isinstance(p, str) else "" for p in prompt])
            if not isinstance(prompt, str):
                prompt = ""

            upstream, response_data = await request_handler.text_completion(
                model=request_data.model,
                prompt=prompt,
                stream=request_data.stream or False,
                reasoning_overrides=request_data.reasoning,
            )

            if request_data.stream:
                # Return streaming response
                if upstream is None:
                    raise HTTPException(status_code=500, detail="Failed to get streaming response")
                return StreamingResponse(
                    request_handler.stream_text_completion(
                        upstream, request_handler._normalize_model_name(request_data.model)
                    ),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                    },
                )
            else:
                # Return non-streaming response
                if response_data is None:
                    raise HTTPException(status_code=500, detail="Failed to get response data")
                return JSONResponse(content=response_data)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    return app
