"""
Models API endpoints for Codex2API.

This module implements the OpenAI-compatible models API endpoints
for listing and retrieving model information.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Path

from ...auth import require_auth
from ...core import (
    get_logger,
    ModelNotFoundError,
    SecurityContext,
    log_error,
)
from ...models import ModelsResponse, ModelInfo, ErrorResponse
from ...services import get_model_manager

# Create router
router = APIRouter(tags=["models"])
logger = get_logger(__name__)


@router.get(
    "/models",
    response_model=ModelsResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="List models",
    description="Lists the currently available models, and provides basic information about each one.",
)
async def list_models(security_context: SecurityContext = Depends(require_auth)) -> ModelsResponse:
    """
    List available models.

    Returns a list of models that are available for use, filtered by
    the user's access level and permissions.
    """
    try:
        model_manager = get_model_manager()

        # Determine user access level
        user_access_level = "public"
        if security_context.has_permission("premium"):
            user_access_level = "premium"
        elif security_context.has_permission("admin"):
            user_access_level = "admin"

        # Get models response
        models_response = model_manager.get_models_response(user_access_level)

        logger.info(
            "Models listed",
            user_id=security_context.user_id,
            access_level=user_access_level,
            models_count=len(models_response.data),
        )

        return models_response

    except Exception as e:
        log_error(logger, e, context={"user_id": security_context.user_id})
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": "Failed to list models", "type": "internal_error"}},
        )


@router.get(
    "/models/{model_id}",
    response_model=Dict[str, Any],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Model Not Found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    },
    summary="Retrieve model",
    description="Retrieves a model instance, providing basic information about the model.",
)
async def retrieve_model(
    model_id: str = Path(..., description="The ID of the model to use for this request"),
    security_context: SecurityContext = Depends(require_auth),
) -> Dict[str, Any]:
    """
    Retrieve detailed information about a specific model.

    Returns detailed information about the specified model including
    capabilities, limitations, and access requirements.
    """
    try:
        model_manager = get_model_manager()

        # Determine user access level
        user_access_level = "public"
        if security_context.has_permission("premium"):
            user_access_level = "premium"
        elif security_context.has_permission("admin"):
            user_access_level = "admin"

        # Validate model access
        model_metadata = model_manager.validate_model_access(model_id, user_access_level)

        # Build detailed response
        response = {
            "id": model_metadata.id,
            "object": "model",
            "created": int(model_metadata.created.timestamp()),
            "owned_by": model_metadata.provider,
            "name": model_metadata.name,
            "description": model_metadata.description,
            "capabilities": {
                "supports_streaming": model_metadata.capabilities.supports_streaming,
                "supports_functions": model_metadata.capabilities.supports_functions,
                "supports_vision": model_metadata.capabilities.supports_vision,
                "supports_reasoning": model_metadata.capabilities.supports_reasoning,
                "max_tokens": model_metadata.capabilities.max_tokens,
                "context_window": model_metadata.capabilities.context_window,
                "training_cutoff": model_metadata.capabilities.training_cutoff,
            },
            "pricing_tier": model_metadata.pricing_tier,
            "access_level": model_metadata.access_level,
        }

        # Add admin-only fields
        if security_context.has_permission("admin"):
            response["metadata"] = {
                "deprecated": model_metadata.deprecated,
                "replacement_model": model_metadata.replacement_model,
            }

        logger.info(
            "Model retrieved",
            user_id=security_context.user_id,
            model_id=model_id,
            access_level=user_access_level,
        )

        return response

    except ModelNotFoundError as e:
        logger.warning("Model not found", user_id=security_context.user_id, model_id=model_id)
        raise HTTPException(status_code=404, detail=e.to_dict())

    except Exception as e:
        log_error(logger, e, context={"user_id": security_context.user_id, "model_id": model_id})
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": "Failed to retrieve model", "type": "internal_error"}},
        )


@router.get(
    "/models/stats",
    response_model=Dict[str, Any],
    summary="Get model statistics",
    description="Get statistics about available models (admin only).",
)
async def get_model_stats(
    security_context: SecurityContext = Depends(require_auth),
) -> Dict[str, Any]:
    """
    Get model statistics.

    Returns statistics about the available models including counts
    by access level, status, and capabilities.
    """
    # Check admin permission
    if not security_context.has_permission("admin"):
        raise HTTPException(
            status_code=403,
            detail={"error": {"message": "Admin access required", "type": "authorization_error"}},
        )

    try:
        model_manager = get_model_manager()

        # Get basic stats
        stats = model_manager.get_model_stats()

        # Get detailed capability stats
        models = model_manager.list_models(include_deprecated=True)

        capability_stats = {
            "streaming_support": len([m for m in models if m.capabilities.supports_streaming]),
            "function_support": len([m for m in models if m.capabilities.supports_functions]),
            "vision_support": len([m for m in models if m.capabilities.supports_vision]),
            "reasoning_support": len([m for m in models if m.capabilities.supports_reasoning]),
        }

        # Get pricing tier stats
        pricing_stats = {}
        for model in models:
            tier = model.pricing_tier
            pricing_stats[tier] = pricing_stats.get(tier, 0) + 1

        response = {
            "total_stats": stats,
            "capability_stats": capability_stats,
            "pricing_stats": pricing_stats,
            "models_by_provider": {
                "openai": len([m for m in models if m.provider == "openai"]),
            },
        }

        logger.info(
            "Model stats retrieved",
            user_id=security_context.user_id,
            total_models=stats["total_models"],
        )

        return response

    except Exception as e:
        log_error(logger, e, context={"user_id": security_context.user_id})
        raise HTTPException(
            status_code=500,
            detail={
                "error": {"message": "Failed to get model statistics", "type": "internal_error"}
            },
        )


@router.get(
    "/models/capabilities",
    response_model=Dict[str, Any],
    summary="List model capabilities",
    description="List all available model capabilities and their descriptions.",
)
async def list_model_capabilities(
    security_context: SecurityContext = Depends(require_auth),
) -> Dict[str, Any]:
    """
    List model capabilities.

    Returns a comprehensive list of all model capabilities and their
    descriptions to help clients understand what each model can do.
    """
    try:
        capabilities = {
            "streaming": {
                "name": "Streaming Support",
                "description": "Model supports streaming responses for real-time output",
                "type": "boolean",
            },
            "functions": {
                "name": "Function Calling",
                "description": "Model can call external functions and tools",
                "type": "boolean",
            },
            "vision": {
                "name": "Vision Support",
                "description": "Model can process and understand images",
                "type": "boolean",
            },
            "reasoning": {
                "name": "Advanced Reasoning",
                "description": "Model has enhanced reasoning capabilities for complex problems",
                "type": "boolean",
            },
            "max_tokens": {
                "name": "Maximum Tokens",
                "description": "Maximum number of tokens the model can generate in a single response",
                "type": "integer",
            },
            "context_window": {
                "name": "Context Window",
                "description": "Maximum number of tokens the model can consider as context",
                "type": "integer",
            },
            "training_cutoff": {
                "name": "Training Data Cutoff",
                "description": "Date when the model's training data was last updated",
                "type": "string",
            },
        }

        return {"object": "list", "data": capabilities}

    except Exception as e:
        log_error(logger, e, context={"user_id": security_context.user_id})
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": "Failed to list capabilities", "type": "internal_error"}},
        )
