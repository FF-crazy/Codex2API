"""
Model management service for Codex2API.

This module manages available models, their capabilities, and access permissions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from pydantic import BaseModel, Field

from ..core import (
    get_logger,
    ModelNotFoundError,
    AuthorizationError,
)
from ..models import ModelInfo, ModelsResponse


class ModelCapabilities(BaseModel):
    """Model capabilities and limitations."""
    
    supports_streaming: bool = Field(True, description="Supports streaming responses")
    supports_functions: bool = Field(False, description="Supports function calling")
    supports_vision: bool = Field(False, description="Supports image inputs")
    supports_reasoning: bool = Field(False, description="Supports reasoning modes")
    max_tokens: int = Field(4096, description="Maximum tokens per request")
    context_window: int = Field(8192, description="Context window size")
    training_cutoff: Optional[str] = Field(None, description="Training data cutoff date")


class ModelMetadata(BaseModel):
    """Extended model metadata."""
    
    id: str = Field(..., description="Model identifier")
    name: str = Field(..., description="Human-readable model name")
    description: str = Field(..., description="Model description")
    provider: str = Field("openai", description="Model provider")
    capabilities: ModelCapabilities = Field(..., description="Model capabilities")
    pricing_tier: str = Field("standard", description="Pricing tier")
    access_level: str = Field("public", description="Access level (public, premium, restricted)")
    created: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    deprecated: bool = Field(False, description="Whether model is deprecated")
    replacement_model: Optional[str] = Field(None, description="Replacement model if deprecated")


class ModelManager:
    """Manages available models and their metadata."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self._models: Dict[str, ModelMetadata] = {}
        self._initialize_default_models()
    
    def _initialize_default_models(self):
        """Initialize default model configurations."""
        default_models = [
            ModelMetadata(
                id="gpt-4",
                name="GPT-4",
                description="Most capable GPT-4 model, great for complex tasks",
                capabilities=ModelCapabilities(
                    supports_streaming=True,
                    supports_functions=True,
                    supports_vision=False,
                    supports_reasoning=False,
                    max_tokens=4096,
                    context_window=8192,
                    training_cutoff="2023-04"
                ),
                pricing_tier="premium",
                access_level="public"
            ),
            ModelMetadata(
                id="gpt-4-turbo",
                name="GPT-4 Turbo",
                description="Faster and more efficient GPT-4 model",
                capabilities=ModelCapabilities(
                    supports_streaming=True,
                    supports_functions=True,
                    supports_vision=True,
                    supports_reasoning=False,
                    max_tokens=4096,
                    context_window=128000,
                    training_cutoff="2024-04"
                ),
                pricing_tier="premium",
                access_level="public"
            ),
            ModelMetadata(
                id="gpt-4o",
                name="GPT-4o",
                description="Omni-modal GPT-4 model with vision and audio capabilities",
                capabilities=ModelCapabilities(
                    supports_streaming=True,
                    supports_functions=True,
                    supports_vision=True,
                    supports_reasoning=False,
                    max_tokens=4096,
                    context_window=128000,
                    training_cutoff="2024-10"
                ),
                pricing_tier="premium",
                access_level="public"
            ),
            ModelMetadata(
                id="gpt-4o-mini",
                name="GPT-4o Mini",
                description="Smaller, faster version of GPT-4o",
                capabilities=ModelCapabilities(
                    supports_streaming=True,
                    supports_functions=True,
                    supports_vision=True,
                    supports_reasoning=False,
                    max_tokens=16384,
                    context_window=128000,
                    training_cutoff="2024-10"
                ),
                pricing_tier="standard",
                access_level="public"
            ),
            ModelMetadata(
                id="gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                description="Fast and efficient model for most tasks",
                capabilities=ModelCapabilities(
                    supports_streaming=True,
                    supports_functions=True,
                    supports_vision=False,
                    supports_reasoning=False,
                    max_tokens=4096,
                    context_window=16385,
                    training_cutoff="2021-09"
                ),
                pricing_tier="standard",
                access_level="public"
            ),
            ModelMetadata(
                id="o1",
                name="o1",
                description="Advanced reasoning model for complex problems",
                capabilities=ModelCapabilities(
                    supports_streaming=False,
                    supports_functions=False,
                    supports_vision=False,
                    supports_reasoning=True,
                    max_tokens=32768,
                    context_window=200000,
                    training_cutoff="2023-10"
                ),
                pricing_tier="premium",
                access_level="premium"
            ),
            ModelMetadata(
                id="o1-mini",
                name="o1-mini",
                description="Smaller reasoning model for faster responses",
                capabilities=ModelCapabilities(
                    supports_streaming=False,
                    supports_functions=False,
                    supports_vision=False,
                    supports_reasoning=True,
                    max_tokens=65536,
                    context_window=128000,
                    training_cutoff="2023-10"
                ),
                pricing_tier="standard",
                access_level="public"
            ),
            ModelMetadata(
                id="o1-preview",
                name="o1-preview",
                description="Preview version of the o1 reasoning model",
                capabilities=ModelCapabilities(
                    supports_streaming=False,
                    supports_functions=False,
                    supports_vision=False,
                    supports_reasoning=True,
                    max_tokens=32768,
                    context_window=128000,
                    training_cutoff="2023-10"
                ),
                pricing_tier="premium",
                access_level="premium"
            ),
        ]
        
        for model in default_models:
            self._models[model.id] = model
    
    def get_model(self, model_id: str) -> ModelMetadata:
        """
        Get model metadata by ID.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Model metadata
            
        Raises:
            ModelNotFoundError: If model doesn't exist
        """
        if model_id not in self._models:
            raise ModelNotFoundError(
                model_id,
                details={"available_models": list(self._models.keys())}
            )
        
        return self._models[model_id]
    
    def list_models(
        self,
        access_level: Optional[str] = None,
        include_deprecated: bool = False
    ) -> List[ModelMetadata]:
        """
        List available models.
        
        Args:
            access_level: Filter by access level
            include_deprecated: Whether to include deprecated models
            
        Returns:
            List of model metadata
        """
        models = []
        
        for model in self._models.values():
            # Skip deprecated models unless requested
            if model.deprecated and not include_deprecated:
                continue
            
            # Filter by access level
            if access_level and model.access_level != access_level:
                continue
            
            models.append(model)
        
        # Sort by name
        return sorted(models, key=lambda m: m.name)
    
    def get_models_response(
        self,
        user_access_level: str = "public"
    ) -> ModelsResponse:
        """
        Get OpenAI-compatible models response.
        
        Args:
            user_access_level: User's access level
            
        Returns:
            Models response
        """
        # Determine which models user can access
        accessible_levels = {"public"}
        if user_access_level in {"premium", "pro"}:
            accessible_levels.add("premium")
        if user_access_level == "admin":
            accessible_levels.add("restricted")
        
        models = []
        for model in self._models.values():
            if model.access_level in accessible_levels and not model.deprecated:
                model_info = ModelInfo(
                    id=model.id,
                    created=int(model.created.timestamp()),
                    owned_by=model.provider
                )
                models.append(model_info)
        
        return ModelsResponse(data=models)
    
    def validate_model_access(
        self,
        model_id: str,
        user_access_level: str = "public"
    ) -> ModelMetadata:
        """
        Validate user access to a model.
        
        Args:
            model_id: Model identifier
            user_access_level: User's access level
            
        Returns:
            Model metadata if accessible
            
        Raises:
            ModelNotFoundError: If model doesn't exist
            AuthorizationError: If user doesn't have access
        """
        model = self.get_model(model_id)
        
        # Check if model is deprecated
        if model.deprecated:
            if model.replacement_model:
                raise ModelNotFoundError(
                    model_id,
                    details={
                        "deprecated": True,
                        "replacement": model.replacement_model,
                        "message": f"Model {model_id} is deprecated. Use {model.replacement_model} instead."
                    }
                )
            else:
                raise ModelNotFoundError(
                    model_id,
                    details={
                        "deprecated": True,
                        "message": f"Model {model_id} is deprecated and no longer available."
                    }
                )
        
        # Check access level
        required_levels = {
            "public": {"public", "premium", "admin"},
            "premium": {"premium", "admin"},
            "restricted": {"admin"}
        }
        
        allowed_levels = required_levels.get(model.access_level, set())
        if user_access_level not in allowed_levels:
            raise AuthorizationError(
                f"Access denied to model {model_id}",
                details={
                    "required_access": model.access_level,
                    "user_access": user_access_level
                }
            )
        
        return model
    
    def add_model(self, model: ModelMetadata) -> None:
        """
        Add a new model.
        
        Args:
            model: Model metadata to add
        """
        self._models[model.id] = model
        self.logger.info("Model added", model_id=model.id, name=model.name)
    
    def remove_model(self, model_id: str) -> bool:
        """
        Remove a model.
        
        Args:
            model_id: Model identifier
            
        Returns:
            True if model was removed
        """
        if model_id in self._models:
            del self._models[model_id]
            self.logger.info("Model removed", model_id=model_id)
            return True
        return False
    
    def deprecate_model(
        self,
        model_id: str,
        replacement_model: Optional[str] = None
    ) -> bool:
        """
        Deprecate a model.
        
        Args:
            model_id: Model identifier
            replacement_model: Optional replacement model
            
        Returns:
            True if model was deprecated
        """
        if model_id in self._models:
            self._models[model_id].deprecated = True
            if replacement_model:
                self._models[model_id].replacement_model = replacement_model
            
            self.logger.info(
                "Model deprecated",
                model_id=model_id,
                replacement=replacement_model
            )
            return True
        return False
    
    def get_model_stats(self) -> Dict[str, int]:
        """
        Get model statistics.
        
        Returns:
            Dictionary with model statistics
        """
        stats = {
            "total_models": len(self._models),
            "active_models": len([m for m in self._models.values() if not m.deprecated]),
            "deprecated_models": len([m for m in self._models.values() if m.deprecated]),
            "public_models": len([m for m in self._models.values() if m.access_level == "public"]),
            "premium_models": len([m for m in self._models.values() if m.access_level == "premium"]),
            "restricted_models": len([m for m in self._models.values() if m.access_level == "restricted"]),
        }
        
        return stats


# Global model manager instance
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Get the global model manager instance."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
