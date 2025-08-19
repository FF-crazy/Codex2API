"""
OpenAI API proxy service for Codex2API.

This module provides a proxy service that translates OpenAI API requests
to ChatGPT internal API calls, maintaining compatibility with OpenAI clients.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

from ..core import (
    get_logger,
    get_settings,
    OpenAIError,
    ModelNotFoundError,
    ValidationError,
    log_api_call,
    log_error,
)
from ..models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChunk,
    CompletionRequest,
    CompletionResponse,
    ModelsResponse,
    ModelInfo,
    Usage,
    ChatCompletionMessage,
    ChatCompletionChoice,
    CompletionChoice,
)
from ..auth import get_token_manager
from .chatgpt_client import ChatGPTClient


class OpenAIProxyService:
    """Service for proxying OpenAI API requests to ChatGPT."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.token_manager = get_token_manager()
        
        # Supported models mapping
        self.supported_models = {
            "gpt-4": "gpt-4",
            "gpt-4-turbo": "gpt-4-turbo", 
            "gpt-4o": "gpt-4o",
            "gpt-4o-mini": "gpt-4o-mini",
            "gpt-3.5-turbo": "gpt-3.5-turbo",
            "o1": "o1",
            "o1-mini": "o1-mini",
            "o1-preview": "o1-preview",
        }
    
    async def create_chat_completion(
        self,
        request: ChatCompletionRequest,
        user_id: str
    ) -> ChatCompletionResponse | AsyncGenerator[ChatCompletionChunk, None]:
        """
        Create chat completion using ChatGPT.
        
        Args:
            request: Chat completion request
            user_id: User identifier for token lookup
            
        Returns:
            Chat completion response or streaming generator
            
        Raises:
            ModelNotFoundError: If model is not supported
            OpenAIError: If request fails
        """
        # Validate model
        if request.model not in self.supported_models:
            raise ModelNotFoundError(
                request.model,
                details={"supported_models": list(self.supported_models.keys())}
            )
        
        # Get user tokens
        auth_bundle = await self.token_manager.get_valid_tokens(user_id)
        if not auth_bundle:
            raise OpenAIError(
                "No valid authentication tokens found",
                error_code="authentication_required",
                status_code=401
            )
        
        try:
            # Create ChatGPT client
            async with ChatGPTClient(auth_bundle.token_data.access_token) as client:
                if request.stream:
                    # Return streaming generator
                    return self._stream_chat_completion(client, request)
                else:
                    # Return complete response
                    return await self._create_chat_completion(client, request)
                    
        except Exception as e:
            log_error(
                self.logger,
                e,
                context={"user_id": user_id, "model": request.model}
            )
            raise OpenAIError(
                f"Chat completion failed: {str(e)}",
                details={"model": request.model, "error": str(e)}
            )
    
    async def _create_chat_completion(
        self,
        client: ChatGPTClient,
        request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Create non-streaming chat completion."""
        start_time = time.time()
        
        # Make request to ChatGPT
        chatgpt_response = await client.create_chat_completion(request)
        
        # Convert to OpenAI format
        response = ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:29]}",
            created=int(start_time),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatCompletionMessage(
                        role="assistant",
                        content=chatgpt_response.get("content", "")
                    ),
                    finish_reason="stop"
                )
            ],
            usage=Usage(
                prompt_tokens=self._estimate_tokens(request.messages),
                completion_tokens=self._estimate_tokens([{"content": chatgpt_response.get("content", "")}]),
                total_tokens=0  # Will be calculated
            )
        )
        
        # Calculate total tokens
        response.usage.total_tokens = response.usage.prompt_tokens + response.usage.completion_tokens
        
        # Log API call
        duration_ms = (time.time() - start_time) * 1000
        log_api_call(
            self.logger,
            service="chatgpt",
            endpoint="/chat/completions",
            method="POST",
            status_code=200,
            duration_ms=duration_ms
        )
        
        return response
    
    async def _stream_chat_completion(
        self,
        client: ChatGPTClient,
        request: ChatCompletionRequest
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """Create streaming chat completion."""
        start_time = time.time()
        chunk_count = 0
        
        try:
            async for chatgpt_chunk in client.create_chat_completion(request):
                chunk_count += 1
                
                # Convert to OpenAI streaming format
                chunk = ChatCompletionChunk(
                    id=f"chatcmpl-{uuid.uuid4().hex[:29]}",
                    created=int(start_time),
                    model=request.model,
                    choices=[
                        {
                            "index": 0,
                            "delta": {
                                "content": chatgpt_chunk.get("content", "")
                            },
                            "finish_reason": None
                        }
                    ]
                )
                
                yield chunk
            
            # Send final chunk
            final_chunk = ChatCompletionChunk(
                id=f"chatcmpl-{uuid.uuid4().hex[:29]}",
                created=int(start_time),
                model=request.model,
                choices=[
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }
                ],
                usage=Usage(
                    prompt_tokens=self._estimate_tokens(request.messages),
                    completion_tokens=chunk_count,  # Rough estimate
                    total_tokens=self._estimate_tokens(request.messages) + chunk_count
                )
            )
            
            yield final_chunk
            
        except Exception as e:
            log_error(self.logger, e, context={"model": request.model})
            raise
        
        finally:
            # Log streaming completion
            duration_ms = (time.time() - start_time) * 1000
            log_api_call(
                self.logger,
                service="chatgpt",
                endpoint="/chat/completions",
                method="POST",
                status_code=200,
                duration_ms=duration_ms
            )
    
    async def create_completion(
        self,
        request: CompletionRequest,
        user_id: str
    ) -> CompletionResponse:
        """
        Create text completion (legacy endpoint).
        
        Args:
            request: Completion request
            user_id: User identifier
            
        Returns:
            Completion response
            
        Raises:
            OpenAIError: If request fails
        """
        # Convert to chat completion format
        if isinstance(request.prompt, str):
            messages = [{"role": "user", "content": request.prompt}]
        else:
            # Handle list of prompts
            messages = [{"role": "user", "content": prompt} for prompt in request.prompt]
        
        chat_request = ChatCompletionRequest(
            model=request.model,
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            n=request.n,
            stream=request.stream,
            stop=request.stop,
            presence_penalty=request.presence_penalty,
            frequency_penalty=request.frequency_penalty,
            user=request.user
        )
        
        # Get chat completion
        chat_response = await self.create_chat_completion(chat_request, user_id)
        
        # Convert to completion format
        choices = []
        for i, choice in enumerate(chat_response.choices):
            completion_choice = CompletionChoice(
                text=choice.message.content or "",
                index=i,
                finish_reason=choice.finish_reason
            )
            choices.append(completion_choice)
        
        response = CompletionResponse(
            id=f"cmpl-{uuid.uuid4().hex[:29]}",
            created=chat_response.created,
            model=request.model,
            choices=choices,
            usage=chat_response.usage
        )
        
        return response
    
    async def list_models(self) -> ModelsResponse:
        """
        List available models.
        
        Returns:
            Models response
        """
        models = []
        for model_id in self.supported_models.keys():
            model_info = ModelInfo(
                id=model_id,
                created=1640995200,  # Fixed timestamp
                owned_by="openai"
            )
            models.append(model_info)
        
        return ModelsResponse(data=models)
    
    def _estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """
        Estimate token count for messages.
        
        Args:
            messages: List of messages
            
        Returns:
            Estimated token count
        """
        # Simple estimation: ~4 characters per token
        total_chars = 0
        for message in messages:
            content = message.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                # Handle structured content
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        total_chars += len(item["text"])
        
        return max(1, total_chars // 4)
    
    async def validate_request(self, request: ChatCompletionRequest) -> None:
        """
        Validate chat completion request.
        
        Args:
            request: Request to validate
            
        Raises:
            ValidationError: If request is invalid
        """
        # Check model
        if request.model not in self.supported_models:
            raise ValidationError(
                f"Model '{request.model}' is not supported",
                error_code="invalid_model",
                details={"supported_models": list(self.supported_models.keys())}
            )
        
        # Check messages
        if not request.messages:
            raise ValidationError(
                "At least one message is required",
                error_code="missing_messages"
            )
        
        # Check message roles
        valid_roles = {"system", "user", "assistant", "tool"}
        for i, message in enumerate(request.messages):
            if message.role not in valid_roles:
                raise ValidationError(
                    f"Invalid role '{message.role}' in message {i}",
                    error_code="invalid_role",
                    details={"valid_roles": list(valid_roles)}
                )
        
        # Check parameters
        if request.temperature is not None and not (0.0 <= request.temperature <= 2.0):
            raise ValidationError(
                "Temperature must be between 0.0 and 2.0",
                error_code="invalid_temperature"
            )
        
        if request.top_p is not None and not (0.0 <= request.top_p <= 1.0):
            raise ValidationError(
                "top_p must be between 0.0 and 1.0",
                error_code="invalid_top_p"
            )


# Global proxy service instance
_proxy_service: Optional[OpenAIProxyService] = None


def get_openai_proxy() -> OpenAIProxyService:
    """Get the global OpenAI proxy service instance."""
    global _proxy_service
    if _proxy_service is None:
        _proxy_service = OpenAIProxyService()
    return _proxy_service
