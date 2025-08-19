"""
API request models for Codex2API.

This module contains all request-related data models for OpenAI
compatible API endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, ConfigDict


class ChatMessage(BaseModel):
    """
    Individual chat message in a conversation.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    role: Literal["system", "user", "assistant", "tool"] = Field(
        ..., description="Role of the message sender"
    )
    content: Union[str, List[Dict[str, Any]], None] = Field(
        ..., description="Message content (text or structured content)"
    )
    name: Optional[str] = Field(None, description="Optional name of the message sender")
    tool_call_id: Optional[str] = Field(
        None, description="ID of the tool call this message responds to"
    )
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        None, description="Tool calls made by the assistant"
    )


class ChatCompletionRequest(BaseModel):
    """
    Request model for OpenAI chat completions API.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="allow",  # Allow extra fields for forward compatibility
    )

    model: str = Field(..., description="Model identifier (e.g., gpt-5, codex-mini)", min_length=1)
    messages: List[ChatMessage] = Field(..., description="List of chat messages", min_length=1)
    temperature: Optional[float] = Field(
        None, description="Sampling temperature (0.0 to 2.0)", ge=0.0, le=2.0
    )
    top_p: Optional[float] = Field(None, description="Nucleus sampling parameter", ge=0.0, le=1.0)
    n: Optional[int] = Field(1, description="Number of completions to generate", ge=1, le=10)
    stream: bool = Field(False, description="Whether to stream the response")
    stop: Optional[Union[str, List[str]]] = Field(None, description="Stop sequences")
    max_tokens: Optional[int] = Field(
        None, description="Maximum number of tokens to generate", gt=0
    )
    presence_penalty: Optional[float] = Field(
        None, description="Presence penalty (-2.0 to 2.0)", ge=-2.0, le=2.0
    )
    frequency_penalty: Optional[float] = Field(
        None, description="Frequency penalty (-2.0 to 2.0)", ge=-2.0, le=2.0
    )
    logit_bias: Optional[Dict[str, float]] = Field(None, description="Logit bias adjustments")
    user: Optional[str] = Field(None, description="User identifier for tracking")
    tools: Optional[List[Dict[str, Any]]] = Field(
        None, description="Available tools for the model to call"
    )
    tool_choice: Optional[Union[str, Dict[str, Any]]] = Field(
        None, description="Tool choice strategy"
    )
    parallel_tool_calls: bool = Field(True, description="Whether to allow parallel tool calls")
    # ChatGPT-specific parameters
    reasoning_effort: Optional[Literal["low", "medium", "high", "none"]] = Field(
        None, description="Reasoning effort level for ChatGPT"
    )
    reasoning_summary: Optional[Literal["auto", "concise", "detailed", "none"]] = Field(
        None, description="Reasoning summary format"
    )
    reasoning_compat: Optional[Literal["legacy", "o3", "think-tags", "current"]] = Field(
        None, description="Reasoning compatibility mode"
    )


class CompletionRequest(BaseModel):
    """
    Request model for OpenAI text completions API.
    """

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="allow")

    model: str = Field(..., description="Model identifier", min_length=1)
    prompt: Union[str, List[str]] = Field(..., description="Text prompt(s) to complete")
    max_tokens: Optional[int] = Field(16, description="Maximum number of tokens to generate", gt=0)
    temperature: Optional[float] = Field(1.0, description="Sampling temperature", ge=0.0, le=2.0)
    top_p: Optional[float] = Field(1.0, description="Nucleus sampling parameter", ge=0.0, le=1.0)
    n: Optional[int] = Field(1, description="Number of completions to generate", ge=1, le=10)
    stream: bool = Field(False, description="Whether to stream the response")
    logprobs: Optional[int] = Field(
        None, description="Number of log probabilities to return", ge=0, le=5
    )
    echo: bool = Field(False, description="Whether to echo the prompt in the response")
    stop: Optional[Union[str, List[str]]] = Field(None, description="Stop sequences")
    presence_penalty: Optional[float] = Field(0.0, description="Presence penalty", ge=-2.0, le=2.0)
    frequency_penalty: Optional[float] = Field(
        0.0, description="Frequency penalty", ge=-2.0, le=2.0
    )
    best_of: Optional[int] = Field(
        1, description="Number of completions to generate server-side", ge=1, le=20
    )
    logit_bias: Optional[Dict[str, float]] = Field(None, description="Logit bias adjustments")
    user: Optional[str] = Field(None, description="User identifier for tracking")
    suffix: Optional[str] = Field(None, description="Suffix to append after completion")
