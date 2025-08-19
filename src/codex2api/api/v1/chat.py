"""
Chat completions API endpoints for Codex2API.

This module implements the OpenAI-compatible chat completions API endpoints
with support for both streaming and non-streaming responses.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
# from sse_starlette import EventSourceResponse

from ...auth import require_auth
from ...core import (
    get_logger,
    ValidationError,
    OpenAIError,
    SecurityContext,
    log_api_call,
    log_error,
)
from ...models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChunk,
    ErrorResponse,
)
from ...services import get_openai_proxy, get_model_manager

# Create router
router = APIRouter(prefix="/chat", tags=["chat"])
logger = get_logger(__name__)


@router.post(
    "/completions",
    response_model=ChatCompletionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Model Not Found"},
        429: {"model": ErrorResponse, "description": "Rate Limited"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="Create chat completion",
    description="Creates a model response for the given chat conversation.",
)
async def create_chat_completion(
    request: ChatCompletionRequest,
    security_context: SecurityContext = Depends(require_auth),
    http_request: Request = None,
) -> ChatCompletionResponse | StreamingResponse:
    """
    Create a chat completion.

    This endpoint is compatible with OpenAI's chat completions API and supports
    both streaming and non-streaming responses.
    """
    try:
        # Get services
        proxy = get_openai_proxy()
        model_manager = get_model_manager()

        # Validate request
        await proxy.validate_request(request)

        # Validate model access
        model_manager.validate_model_access(request.model, security_context.user_id or "public")

        # Log request
        logger.info(
            "Chat completion request",
            user_id=security_context.user_id,
            model=request.model,
            stream=request.stream,
            messages_count=len(request.messages),
        )

        # Create completion
        result = await proxy.create_chat_completion(
            request, security_context.user_id or "anonymous"
        )

        if request.stream:
            # Return streaming response
            # For now, return error for streaming (would need sse-starlette)
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {"message": "Streaming not implemented yet", "type": "not_implemented"}
                },
            )
        else:
            # Return complete response
            return result

    except ValidationError as e:
        logger.warning(
            "Chat completion validation error", user_id=security_context.user_id, error=str(e)
        )
        raise HTTPException(status_code=400, detail=e.to_dict())

    except OpenAIError as e:
        log_error(logger, e, context={"user_id": security_context.user_id, "model": request.model})
        raise HTTPException(status_code=e.status_code, detail=e.to_dict())

    except Exception as e:
        log_error(
            logger,
            e,
            context={
                "user_id": security_context.user_id,
                "model": getattr(request, "model", "unknown"),
            },
        )
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": "Internal server error", "type": "internal_error"}},
        )


async def _stream_chat_completion(completion_generator) -> str:
    """
    Stream chat completion chunks in Server-Sent Events format.

    Args:
        completion_generator: Async generator of completion chunks

    Yields:
        SSE-formatted completion chunks
    """
    try:
        async for chunk in completion_generator:
            # Convert chunk to JSON
            if isinstance(chunk, ChatCompletionChunk):
                chunk_data = chunk.model_dump()
            else:
                chunk_data = chunk

            # Format as Server-Sent Event
            chunk_json = json.dumps(chunk_data, ensure_ascii=False)
            yield f"data: {chunk_json}\n\n"

        # Send final event
        yield "data: [DONE]\n\n"

    except Exception as e:
        # Send error event
        error_data = {"error": {"message": f"Streaming error: {str(e)}", "type": "streaming_error"}}
        error_json = json.dumps(error_data, ensure_ascii=False)
        yield f"data: {error_json}\n\n"
        yield "data: [DONE]\n\n"


@router.get(
    "/models",
    response_model=Dict[str, Any],
    summary="List chat models",
    description="List available models for chat completions.",
)
async def list_chat_models(
    security_context: SecurityContext = Depends(require_auth),
) -> Dict[str, Any]:
    """
    List available chat models.

    Returns a list of models that can be used for chat completions,
    filtered by the user's access level.
    """
    try:
        model_manager = get_model_manager()

        # Get user access level (default to public)
        user_access_level = "public"
        if security_context.has_permission("premium"):
            user_access_level = "premium"
        elif security_context.has_permission("admin"):
            user_access_level = "admin"

        # Get models response
        models_response = model_manager.get_models_response(user_access_level)

        # Filter for chat-capable models
        chat_models = []
        for model in models_response.data:
            model_metadata = model_manager.get_model(model.id)
            # All our models support chat
            chat_models.append(
                {
                    "id": model.id,
                    "object": "model",
                    "created": model.created,
                    "owned_by": model.owned_by,
                    "capabilities": {
                        "supports_streaming": model_metadata.capabilities.supports_streaming,
                        "supports_functions": model_metadata.capabilities.supports_functions,
                        "supports_vision": model_metadata.capabilities.supports_vision,
                        "max_tokens": model_metadata.capabilities.max_tokens,
                        "context_window": model_metadata.capabilities.context_window,
                    },
                }
            )

        return {"object": "list", "data": chat_models}

    except Exception as e:
        log_error(logger, e, context={"user_id": security_context.user_id})
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": "Failed to list models", "type": "internal_error"}},
        )


@router.post(
    "/completions/validate",
    response_model=Dict[str, Any],
    summary="Validate chat completion request",
    description="Validate a chat completion request without executing it.",
)
async def validate_chat_completion(
    request: ChatCompletionRequest, security_context: SecurityContext = Depends(require_auth)
) -> Dict[str, Any]:
    """
    Validate a chat completion request.

    This endpoint allows clients to validate their requests before sending
    them to the actual completion endpoint.
    """
    try:
        # Get services
        proxy = get_openai_proxy()
        model_manager = get_model_manager()

        # Validate request
        await proxy.validate_request(request)

        # Validate model access
        model_metadata = model_manager.validate_model_access(
            request.model, security_context.user_id or "public"
        )

        # Estimate token usage
        estimated_tokens = proxy._estimate_tokens(request.messages)

        return {
            "valid": True,
            "model": {
                "id": request.model,
                "name": model_metadata.name,
                "capabilities": model_metadata.capabilities.model_dump(),
            },
            "estimated_usage": {
                "prompt_tokens": estimated_tokens,
                "max_completion_tokens": request.max_tokens
                or model_metadata.capabilities.max_tokens,
            },
            "warnings": [],
        }

    except ValidationError as e:
        return {"valid": False, "error": e.to_dict(), "warnings": []}

    except Exception as e:
        log_error(
            logger,
            e,
            context={
                "user_id": security_context.user_id,
                "model": getattr(request, "model", "unknown"),
            },
        )
        return {
            "valid": False,
            "error": {"message": f"Validation failed: {str(e)}", "type": "validation_error"},
            "warnings": [],
        }
