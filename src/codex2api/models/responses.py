"""
API response models for Codex2API.

This module contains all response-related data models for OpenAI
compatible API endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, ConfigDict


class Usage(BaseModel):
    """
    Token usage information.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    prompt_tokens: int = Field(..., description="Number of tokens in the prompt", ge=0)
    completion_tokens: int = Field(..., description="Number of tokens in the completion", ge=0)
    total_tokens: int = Field(..., description="Total number of tokens used", ge=0)


class ToolCall(BaseModel):
    """
    Tool call information.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    id: str = Field(..., description="Unique identifier for the tool call", min_length=1)
    type: Literal["function"] = Field("function", description="Type of tool call")
    function: Dict[str, Any] = Field(..., description="Function call details")


class ChatCompletionMessage(BaseModel):
    """
    Chat completion message in response.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    role: Literal["assistant", "system", "user", "tool"] = Field(
        ..., description="Role of the message sender"
    )
    content: Optional[str] = Field(None, description="Message content")
    tool_calls: Optional[List[ToolCall]] = Field(
        None, description="Tool calls made by the assistant"
    )
    refusal: Optional[str] = Field(None, description="Refusal message if request was refused")


class ChatCompletionChoice(BaseModel):
    """
    Individual choice in chat completion response.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    index: int = Field(..., description="Index of this choice", ge=0)
    message: ChatCompletionMessage = Field(..., description="The completion message")
    finish_reason: Optional[
        Literal["stop", "length", "tool_calls", "content_filter", "function_call"]
    ] = Field(None, description="Reason why the completion finished")
    logprobs: Optional[Dict[str, Any]] = Field(None, description="Log probabilities for tokens")


class ChatCompletionResponse(BaseModel):
    """
    Response model for chat completions API.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    id: str = Field(..., description="Unique identifier for the completion", min_length=1)
    object: Literal["chat.completion"] = Field("chat.completion", description="Object type")
    created: int = Field(..., description="Unix timestamp of creation", gt=0)
    model: str = Field(..., description="Model used for completion", min_length=1)
    choices: List[ChatCompletionChoice] = Field(
        ..., description="List of completion choices", min_length=1
    )
    usage: Optional[Usage] = Field(None, description="Token usage information")
    system_fingerprint: Optional[str] = Field(None, description="System fingerprint")


class ChatCompletionChunk(BaseModel):
    """
    Streaming chunk for chat completions.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    id: str = Field(..., description="Unique identifier for the completion", min_length=1)
    object: Literal["chat.completion.chunk"] = Field(
        "chat.completion.chunk", description="Object type"
    )
    created: int = Field(..., description="Unix timestamp of creation", gt=0)
    model: str = Field(..., description="Model used for completion", min_length=1)
    choices: List[Dict[str, Any]] = Field(..., description="List of completion choice deltas")
    usage: Optional[Usage] = Field(None, description="Token usage information (final chunk only)")


class CompletionChoice(BaseModel):
    """
    Individual choice in text completion response.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    text: str = Field(..., description="The completion text")
    index: int = Field(..., description="Index of this choice", ge=0)
    logprobs: Optional[Dict[str, Any]] = Field(None, description="Log probabilities for tokens")
    finish_reason: Optional[Literal["stop", "length", "content_filter"]] = Field(
        None, description="Reason why the completion finished"
    )


class CompletionResponse(BaseModel):
    """
    Response model for text completions API.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    id: str = Field(..., description="Unique identifier for the completion", min_length=1)
    object: Literal["text_completion"] = Field("text_completion", description="Object type")
    created: int = Field(..., description="Unix timestamp of creation", gt=0)
    model: str = Field(..., description="Model used for completion", min_length=1)
    choices: List[CompletionChoice] = Field(
        ..., description="List of completion choices", min_length=1
    )
    usage: Optional[Usage] = Field(None, description="Token usage information")


class ModelInfo(BaseModel):
    """
    Information about a single model.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    id: str = Field(..., description="Model identifier", min_length=1)
    object: Literal["model"] = Field("model", description="Object type")
    created: int = Field(..., description="Unix timestamp of model creation", gt=0)
    owned_by: str = Field("openai", description="Organization that owns the model")


class ModelsResponse(BaseModel):
    """
    Response model for models list API.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    object: Literal["list"] = Field("list", description="Object type")
    data: List[ModelInfo] = Field(..., description="List of available models")


class ErrorResponse(BaseModel):
    """
    Standard error response model.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    error: Dict[str, Any] = Field(..., description="Error details")
