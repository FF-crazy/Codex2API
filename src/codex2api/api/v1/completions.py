"""
Text completions API endpoints for Codex2API.

This module implements the OpenAI-compatible text completions API endpoints
for backward compatibility with legacy applications.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from ...auth import require_auth
from ...core import (
    get_logger,
    ValidationError,
    OpenAIError,
    SecurityContext,
    log_error,
)
from ...models import (
    CompletionRequest,
    CompletionResponse,
    ErrorResponse,
)
from ...services import get_openai_proxy, get_model_manager

# Create router
router = APIRouter(tags=["completions"])
logger = get_logger(__name__)


@router.post(
    "/completions",
    response_model=CompletionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Model Not Found"},
        429: {"model": ErrorResponse, "description": "Rate Limited"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="Create text completion",
    description="Creates a completion for the provided prompt and parameters. This is the legacy endpoint.",
    deprecated=True,
)
async def create_completion(
    request: CompletionRequest,
    security_context: SecurityContext = Depends(require_auth),
    http_request: Request = None,
) -> CompletionResponse | StreamingResponse:
    """
    Create a text completion.

    This endpoint is compatible with OpenAI's legacy completions API.
    It's recommended to use the chat completions API instead.
    """
    try:
        # Get services
        proxy = get_openai_proxy()
        model_manager = get_model_manager()

        # Validate model exists and user has access
        model_manager.validate_model_access(request.model, security_context.user_id or "public")

        # Log request
        logger.info(
            "Text completion request",
            user_id=security_context.user_id,
            model=request.model,
            stream=request.stream,
            prompt_type=type(request.prompt).__name__,
        )

        # Create completion
        result = await proxy.create_completion(request, security_context.user_id or "anonymous")

        if request.stream:
            # For streaming, we'd need to implement streaming text completions
            # For now, we'll return an error
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "message": "Streaming text completions are not supported. Use chat completions instead.",
                        "type": "invalid_request_error",
                        "code": "streaming_not_supported",
                    }
                },
            )
        else:
            return result

    except ValidationError as e:
        logger.warning(
            "Text completion validation error", user_id=security_context.user_id, error=str(e)
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


@router.get(
    "/completions/models",
    response_model=Dict[str, Any],
    summary="List completion models",
    description="List available models for text completions.",
    deprecated=True,
)
async def list_completion_models(
    security_context: SecurityContext = Depends(require_auth),
) -> Dict[str, Any]:
    """
    List available text completion models.

    Returns a list of models that can be used for text completions.
    This is a legacy endpoint - use /v1/models instead.
    """
    try:
        model_manager = get_model_manager()

        # Get user access level
        user_access_level = "public"
        if security_context.has_permission("premium"):
            user_access_level = "premium"
        elif security_context.has_permission("admin"):
            user_access_level = "admin"

        # Get models response
        models_response = model_manager.get_models_response(user_access_level)

        # Filter for completion-capable models (all our models support this)
        completion_models = []
        for model in models_response.data:
            model_metadata = model_manager.get_model(model.id)
            completion_models.append(
                {
                    "id": model.id,
                    "object": "model",
                    "created": model.created,
                    "owned_by": model.owned_by,
                    "capabilities": {
                        "max_tokens": model_metadata.capabilities.max_tokens,
                        "context_window": model_metadata.capabilities.context_window,
                    },
                }
            )

        return {"object": "list", "data": completion_models}

    except Exception as e:
        log_error(logger, e, context={"user_id": security_context.user_id})
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": "Failed to list models", "type": "internal_error"}},
        )


@router.post(
    "/completions/validate",
    response_model=Dict[str, Any],
    summary="Validate completion request",
    description="Validate a text completion request without executing it.",
    deprecated=True,
)
async def validate_completion(
    request: CompletionRequest, security_context: SecurityContext = Depends(require_auth)
) -> Dict[str, Any]:
    """
    Validate a text completion request.

    This endpoint allows clients to validate their requests before sending
    them to the actual completion endpoint.
    """
    try:
        model_manager = get_model_manager()

        # Validate model access
        model_metadata = model_manager.validate_model_access(
            request.model, security_context.user_id or "public"
        )

        # Basic validation
        warnings = []

        # Check if model supports the requested features
        if request.stream:
            warnings.append(
                {
                    "code": "streaming_not_supported",
                    "message": "Streaming is not supported for text completions",
                }
            )

        # Check prompt length
        if isinstance(request.prompt, str):
            prompt_length = len(request.prompt)
        elif isinstance(request.prompt, list):
            prompt_length = sum(len(str(p)) for p in request.prompt)
        else:
            prompt_length = 0

        if prompt_length > model_metadata.capabilities.context_window * 4:  # Rough estimate
            warnings.append(
                {
                    "code": "prompt_too_long",
                    "message": f"Prompt may exceed model's context window ({model_metadata.capabilities.context_window} tokens)",
                }
            )

        # Estimate token usage
        estimated_prompt_tokens = max(1, prompt_length // 4)

        return {
            "valid": True,
            "model": {
                "id": request.model,
                "name": model_metadata.name,
                "capabilities": model_metadata.capabilities.model_dump(),
            },
            "estimated_usage": {
                "prompt_tokens": estimated_prompt_tokens,
                "max_completion_tokens": request.max_tokens
                or model_metadata.capabilities.max_tokens,
            },
            "warnings": warnings,
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
