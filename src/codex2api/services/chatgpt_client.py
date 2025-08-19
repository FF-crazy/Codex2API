"""
ChatGPT client for Codex2API.

This module provides a client for interacting with ChatGPT's internal API,
handling conversation management and message streaming.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

from ..core import (
    get_logger,
    ChatGPTError,
    log_api_call,
    log_error,
)
from ..models import ChatMessage, ChatCompletionRequest, TokenData
from ..utils.http_client import ChatGPTHTTPClient


class ChatGPTClient:
    """Client for ChatGPT internal API."""

    def __init__(self, access_token: Optional[str] = None):
        self.logger = get_logger(__name__)
        self.http_client = ChatGPTHTTPClient(access_token)
        self._conversation_cache: Dict[str, str] = {}  # conversation_id -> parent_message_id

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.http_client.close()

    def set_access_token(self, access_token: str):
        """Update access token."""
        self.http_client.set_access_token(access_token)

    async def create_chat_completion(
        self, request: ChatCompletionRequest, conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a chat completion using ChatGPT.

        Args:
            request: Chat completion request
            conversation_id: Optional conversation ID for continuity

        Returns:
            Chat completion response

        Raises:
            ChatGPTError: If request fails
        """
        try:
            # Convert OpenAI format to ChatGPT format
            chatgpt_request = self._convert_to_chatgpt_format(request, conversation_id)

            if request.stream:
                # Handle streaming response
                return await self._create_streaming_completion(chatgpt_request)
            else:
                # Handle non-streaming response
                return await self._create_completion(chatgpt_request)

        except Exception as e:
            log_error(
                self.logger, e, context={"model": request.model, "conversation_id": conversation_id}
            )
            raise ChatGPTError(
                f"Failed to create chat completion: {str(e)}",
                details={"model": request.model, "error": str(e)},
            )

    async def _create_completion(self, chatgpt_request: Dict[str, Any]) -> Dict[str, Any]:
        """Create non-streaming completion."""
        response = await self.http_client.post("/backend-api/conversation", json=chatgpt_request)

        if response.status_code != 200:
            raise ChatGPTError(
                f"ChatGPT API error: {response.status_code}",
                status_code=response.status_code,
                details={"response": response.text},
            )

        # Parse ChatGPT response and convert to OpenAI format
        chatgpt_response = response.json()
        return self._convert_to_openai_format(chatgpt_response, False)

    async def _create_streaming_completion(
        self, chatgpt_request: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Create streaming completion."""
        try:
            async for chunk in self.http_client.stream_request(
                "POST", "/backend-api/conversation", json=chatgpt_request
            ):
                # Parse Server-Sent Events format
                chunk_str = chunk.decode("utf-8")

                for line in chunk_str.split("\n"):
                    if line.startswith("data: "):
                        data = line[6:]  # Remove 'data: ' prefix

                        if data == "[DONE]":
                            return

                        try:
                            chunk_data = json.loads(data)
                            # Convert ChatGPT chunk to OpenAI format
                            openai_chunk = self._convert_chunk_to_openai_format(chunk_data)
                            if openai_chunk:
                                yield openai_chunk
                        except json.JSONDecodeError:
                            continue

        except Exception as e:
            log_error(self.logger, e, context={"request": chatgpt_request})
            raise ChatGPTError(f"Streaming completion failed: {str(e)}", details={"error": str(e)})

    def _convert_to_chatgpt_format(
        self, request: ChatCompletionRequest, conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert OpenAI chat completion request to ChatGPT format.

        Args:
            request: OpenAI format request
            conversation_id: Optional conversation ID

        Returns:
            ChatGPT format request
        """
        # Generate IDs
        message_id = str(uuid.uuid4())
        conversation_id = conversation_id or str(uuid.uuid4())

        # Get parent message ID from cache or generate new
        parent_message_id = self._conversation_cache.get(conversation_id, str(uuid.uuid4()))

        # Convert messages to ChatGPT format
        # For simplicity, we'll use the last user message
        user_message = None
        system_message = None

        for msg in request.messages:
            if msg.role == "user":
                user_message = msg.content
            elif msg.role == "system":
                system_message = msg.content

        if not user_message:
            raise ChatGPTError("No user message found in request")

        # Build ChatGPT request
        chatgpt_request = {
            "action": "next",
            "messages": [
                {
                    "id": message_id,
                    "author": {"role": "user"},
                    "content": {"content_type": "text", "parts": [user_message]},
                    "metadata": {},
                }
            ],
            "conversation_id": conversation_id,
            "parent_message_id": parent_message_id,
            "model": self._map_model_name(request.model),
            "timezone_offset_min": 0,
            "suggestions": [],
            "history_and_training_disabled": False,
            "conversation_mode": {"kind": "primary_assistant"},
            "force_paragen": False,
            "force_paragen_model_slug": "",
            "force_rate_limit": False,
        }

        # Add system message if present
        if system_message:
            chatgpt_request["system_hints"] = [system_message]

        # Add reasoning parameters for o1 models
        if request.reasoning_effort:
            chatgpt_request["reasoning_effort"] = request.reasoning_effort

        if request.reasoning_summary:
            chatgpt_request["reasoning_summary"] = request.reasoning_summary

        if request.reasoning_compat:
            chatgpt_request["reasoning_compat"] = request.reasoning_compat

        # Store conversation state
        self._conversation_cache[conversation_id] = message_id

        return chatgpt_request

    def _map_model_name(self, openai_model: str) -> str:
        """
        Map OpenAI model names to ChatGPT model names.

        Args:
            openai_model: OpenAI model name

        Returns:
            ChatGPT model name
        """
        model_mapping = {
            "gpt-4": "gpt-4",
            "gpt-4-turbo": "gpt-4-turbo",
            "gpt-4o": "gpt-4o",
            "gpt-4o-mini": "gpt-4o-mini",
            "gpt-3.5-turbo": "gpt-3.5-turbo",
            "o1": "o1",
            "o1-mini": "o1-mini",
            "o1-preview": "o1-preview",
        }

        return model_mapping.get(openai_model, "gpt-4")

    def _convert_to_openai_format(
        self, chatgpt_response: Dict[str, Any], is_streaming: bool = False
    ) -> Dict[str, Any]:
        """
        Convert ChatGPT response to OpenAI format.

        Args:
            chatgpt_response: ChatGPT format response
            is_streaming: Whether this is a streaming response

        Returns:
            OpenAI format response
        """
        # Extract message content from ChatGPT response
        message_content = ""
        if "message" in chatgpt_response and "content" in chatgpt_response["message"]:
            content = chatgpt_response["message"]["content"]
            if "parts" in content and content["parts"]:
                message_content = content["parts"][0]

        # Build OpenAI response
        response = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:29]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "gpt-4",  # Default model
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": message_content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 0,  # ChatGPT doesn't provide token counts
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }

        return response

    def _convert_chunk_to_openai_format(
        self, chatgpt_chunk: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Convert ChatGPT streaming chunk to OpenAI format.

        Args:
            chatgpt_chunk: ChatGPT format chunk

        Returns:
            OpenAI format chunk or None if not convertible
        """
        # Extract content from ChatGPT chunk
        if "message" not in chatgpt_chunk:
            return None

        message = chatgpt_chunk["message"]
        if "content" not in message or "parts" not in message["content"]:
            return None

        parts = message["content"]["parts"]
        if not parts:
            return None

        content = parts[0] if parts else ""

        # Build OpenAI streaming chunk
        chunk = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:29]}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "gpt-4",
            "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}],
        }

        return chunk

    async def get_conversations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get list of conversations.

        Args:
            limit: Maximum number of conversations to return

        Returns:
            List of conversation metadata
        """
        try:
            response = await self.http_client.get(
                "/backend-api/conversations", params={"offset": 0, "limit": limit}
            )

            if response.status_code != 200:
                raise ChatGPTError(
                    f"Failed to get conversations: {response.status_code}",
                    status_code=response.status_code,
                )

            return response.json().get("items", [])

        except Exception as e:
            log_error(self.logger, e)
            raise ChatGPTError(f"Failed to get conversations: {str(e)}")

    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation.

        Args:
            conversation_id: Conversation ID to delete

        Returns:
            True if successful
        """
        try:
            response = await self.http_client.delete(f"/backend-api/conversation/{conversation_id}")

            # Remove from cache
            self._conversation_cache.pop(conversation_id, None)

            return response.status_code == 200

        except Exception as e:
            log_error(self.logger, e, context={"conversation_id": conversation_id})
            return False
