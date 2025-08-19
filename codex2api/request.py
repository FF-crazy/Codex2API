"""
Request handling module for Codex2API.

This module handles all interactions with the ChatGPT API, including
authentication, request forwarding, and response processing.
"""

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def load_supported_models() -> List[str]:
    """Load supported model names from models.json file."""
    models_paths = [
        "models.json",  # Current directory
        os.path.join(os.path.dirname(__file__), "..", "models.json"),  # Parent directory
    ]

    for path in models_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                models = data.get("models", [])
                return [
                    model.get("id", model.get("name", ""))
                    for model in models
                    if model.get("id") or model.get("name")
                ]
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"Warning: Failed to read models file {path}: {e}")
            continue

    # Fallback to default models if file not found
    return ["gpt-5", "gpt-4o", "gpt-4", "gpt-3.5-turbo"]


def read_auth_file() -> Optional[Dict[str, Any]]:
    """Read authentication data from auth.json file."""
    auth_paths = [
        "auth.json",  # Current directory
        os.path.expanduser("~/.chatgpt-local/auth.json"),
        os.path.expanduser("~/.codex/auth.json"),
    ]

    for path in auth_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"Warning: Failed to read auth file {path}: {e}")
            continue

    return None


def get_effective_chatgpt_auth() -> Tuple[Optional[str], Optional[str]]:
    """Get effective ChatGPT authentication from auth.json."""
    auth = read_auth_file()
    if not auth:
        return None, None

    tokens = auth.get("tokens", {})
    access_token = tokens.get("access_token")
    account_id = tokens.get("account_id")

    return access_token, account_id


def convert_chat_messages_to_responses_input(
    messages: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Convert chat messages to ChatGPT responses input format."""
    input_items: List[Dict[str, Any]] = []

    for message in messages:
        role = message.get("role")
        if role == "system":
            continue

        content = message.get("content", "")
        if isinstance(content, str) and content:
            kind = "output_text" if role == "assistant" else "input_text"
            content_items = [{"type": kind, "text": content}]
            role_out = "assistant" if role == "assistant" else "user"
            input_items.append({"type": "message", "role": role_out, "content": content_items})

    return input_items


def convert_tools_chat_to_responses(tools: Any) -> List[Dict[str, Any]]:
    """Convert tools from chat format to responses format."""
    out: List[Dict[str, Any]] = []
    if not isinstance(tools, list):
        return out

    for t in tools:
        if not isinstance(t, dict) or t.get("type") != "function":
            continue

        fn = t.get("function", {})
        name = fn.get("name")
        if not isinstance(name, str) or not name:
            continue

        desc = fn.get("description", "")
        params = fn.get("parameters", {"type": "object", "properties": {}})

        out.append(
            {
                "type": "function",
                "name": name,
                "description": desc,
                "strict": False,
                "parameters": params,
            }
        )

    return out


# Constants
CHATGPT_RESPONSES_URL = "https://chatgpt.com/backend-api/codex/responses"


def read_base_instructions() -> str:
    """Read base instructions from codex2api/prompt.md, always override user instructions."""
    # Always use our own prompt.md file, prioritizing codex2api/prompt.md
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "prompt.md"),  # codex2api/prompt.md (priority)
        os.path.join(os.path.dirname(__file__), "..", "ChatMock", "prompt.md"),  # ChatMock fallback
        os.path.join(os.path.dirname(__file__), "..", "..", "ChatMock", "prompt.md"),
        "ChatMock/prompt.md",
        "codex2api/prompt.md",
    ]

    for prompt_path in possible_paths:
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                content = f.read()
                if isinstance(content, str) and content.strip():
                    print(f"✅ Loaded instructions from {prompt_path} ({len(content)} chars)")
                    return content
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"⚠️  Error reading {prompt_path}: {e}")
            continue

    # Fallback instructions if no prompt.md found
    print("⚠️  Using fallback instructions (no prompt.md found)")
    return """You are ChatGPT, a large language model trained by OpenAI. You are a helpful, harmless, and honest AI assistant.

You should:
- Provide accurate and helpful information to the best of your knowledge
- Be clear and concise in your responses
- Acknowledge when you don't know something or when information might be uncertain
- Avoid generating harmful, biased, or inappropriate content
- Respect user privacy and confidentiality"""


BASE_INSTRUCTIONS = read_base_instructions()


class ChatGPTRequestHandler:
    """Handles requests to ChatGPT API."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.client = httpx.AsyncClient(timeout=600.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    def _log(self, message: str) -> None:
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[REQUEST] {message}")

    def _build_reasoning_param(self, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Build reasoning parameter for ChatGPT API."""
        reasoning_param = {
            "effort": "medium",
            "summary": "auto",  # Use "auto" instead of boolean
        }
        if isinstance(overrides, dict):
            reasoning_param.update(overrides)
        return reasoning_param

    def _normalize_model_name(self, model: str) -> str:
        """Normalize model name for ChatGPT API."""
        if not isinstance(model, str):
            return "gpt-5"

        model = model.strip().lower()
        supported_models = [m.lower() for m in load_supported_models()]

        # If the model is in our supported list, use it
        if model in supported_models:
            # For now, we still map everything to gpt-5 for the actual API call
            # but we validate against the models.json file
            return "gpt-5"

        # Default fallback
        return "gpt-5"

    async def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for ChatGPT API."""
        access_token, account_id = get_effective_chatgpt_auth()
        if not access_token or not account_id:
            raise HTTPException(
                status_code=401, detail="Missing ChatGPT credentials. Please authenticate first."
            )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "chatgpt-account-id": account_id,
        }
        headers["OpenAI-Beta"] = "responses=experimental"
        return headers

    async def _start_upstream_request(
        self,
        model: str,
        input_items: List[Dict[str, Any]],
        instructions: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Any = None,
        parallel_tool_calls: bool = False,
        reasoning_param: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Start upstream request to ChatGPT API."""
        headers = await self._get_auth_headers()

        reasoning_param = (
            reasoning_param if isinstance(reasoning_param, dict) else self._build_reasoning_param()
        )
        include: List[str] = []
        if isinstance(reasoning_param, dict) and reasoning_param.get("effort") != "none":
            include.append("reasoning.encrypted_content")

        # Always use our own instructions, ignore user-provided instructions
        responses_payload = {
            "model": model,
            "instructions": BASE_INSTRUCTIONS,  # Always use our prompt.md content
            "input": input_items,
            "tools": tools or [],
            "tool_choice": tool_choice
            if tool_choice in ("auto", "none") or isinstance(tool_choice, dict)
            else "auto",
            "parallel_tool_calls": bool(parallel_tool_calls),
            "store": False,
            "stream": True,
            "include": include,
        }

        if reasoning_param is not None:
            responses_payload["reasoning"] = reasoning_param

        self._log(
            f"Sending request to ChatGPT API: {json.dumps(responses_payload, indent=2)[:500]}..."
        )

        try:
            response = await self.client.post(
                CHATGPT_RESPONSES_URL,
                headers=headers,
                json=responses_payload,
            )
            response.raise_for_status()
            return response
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Upstream ChatGPT request failed: {e}")
        except httpx.HTTPStatusError as e:
            error_detail = f"ChatGPT API error: {e.response.text}"

            # Check for common error patterns
            if e.response.status_code == 403:
                if (
                    "cloudflare" in e.response.text.lower()
                    or "challenge" in e.response.text.lower()
                ):
                    error_detail = "Authentication failed: ChatGPT token may be expired or blocked by Cloudflare. Please re-authenticate."
                else:
                    error_detail = "Access denied: ChatGPT token may be expired or invalid. Please re-authenticate."
            elif e.response.status_code == 401:
                error_detail = (
                    "Unauthorized: ChatGPT token is invalid or expired. Please re-authenticate."
                )

            raise HTTPException(status_code=e.response.status_code, detail=error_detail)

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        stream: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Any = None,
        parallel_tool_calls: bool = False,
        reasoning_overrides: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Tuple[Optional[httpx.Response], Optional[Dict[str, Any]]]:
        """Handle chat completion request."""
        normalized_model = self._normalize_model_name(model)
        input_items = convert_chat_messages_to_responses_input(messages)
        tools_responses = convert_tools_chat_to_responses(tools or [])

        upstream = await self._start_upstream_request(
            normalized_model,
            input_items,
            instructions=BASE_INSTRUCTIONS,
            tools=tools_responses,
            tool_choice=tool_choice,
            parallel_tool_calls=parallel_tool_calls,
            reasoning_param=self._build_reasoning_param(reasoning_overrides),
        )

        if stream:
            return upstream, None
        else:
            # Process non-streaming response
            response_data = await self._process_non_streaming_response(upstream, normalized_model)
            return None, response_data

    async def text_completion(
        self,
        model: str,
        prompt: str,
        stream: bool = False,
        reasoning_overrides: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Tuple[Optional[httpx.Response], Optional[Dict[str, Any]]]:
        """Handle text completion request."""
        normalized_model = self._normalize_model_name(model)
        messages = [{"role": "user", "content": prompt or ""}]
        input_items = convert_chat_messages_to_responses_input(messages)

        upstream = await self._start_upstream_request(
            normalized_model,
            input_items,
            instructions=BASE_INSTRUCTIONS,
            reasoning_param=self._build_reasoning_param(reasoning_overrides),
        )

        if stream:
            return upstream, None
        else:
            # Process non-streaming response for text completion
            response_data = await self._process_text_completion_response(upstream, normalized_model)
            return None, response_data

    async def _process_non_streaming_response(
        self, upstream: httpx.Response, model: str
    ) -> Dict[str, Any]:
        """Process non-streaming chat completion response."""
        created = int(time.time())
        response_id = "chatcmpl"
        full_text = ""
        tool_calls = []
        error_message = ""

        try:
            async for raw_line in upstream.aiter_lines():
                if not raw_line:
                    continue
                line = raw_line.strip()
                if not line.startswith("data: "):
                    continue
                data = line[len("data: ") :].strip()
                if not data or data == "[DONE]":
                    if data == "[DONE]":
                        break
                    continue

                try:
                    evt = json.loads(data)
                except Exception:
                    continue

                if isinstance(evt.get("response"), dict) and isinstance(
                    evt["response"].get("id"), str
                ):
                    response_id = evt["response"].get("id") or response_id

                kind = evt.get("type")
                if kind == "response.output_text.delta":
                    full_text += evt.get("delta") or ""
                elif kind == "response.output_item.done":
                    item = evt.get("item") or {}
                    if isinstance(item, dict) and item.get("type") == "function_call":
                        call_id = item.get("call_id") or item.get("id") or ""
                        name = item.get("name") or ""
                        args = item.get("arguments") or ""
                        if (
                            isinstance(call_id, str)
                            and isinstance(name, str)
                            and isinstance(args, str)
                        ):
                            tool_calls.append(
                                {
                                    "id": call_id,
                                    "type": "function",
                                    "function": {"name": name, "arguments": args},
                                }
                            )
                elif kind == "response.failed":
                    error_message = (
                        evt.get("response", {}).get("error", {}).get("message", "response.failed")
                    )
                elif kind == "response.completed":
                    break
        finally:
            await upstream.aclose()

        if error_message:
            raise HTTPException(status_code=502, detail=error_message)

        message = {"role": "assistant", "content": full_text if full_text else None}
        if tool_calls:
            message["tool_calls"] = tool_calls

        return {
            "id": response_id,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": "stop",
                }
            ],
        }

    async def _process_text_completion_response(
        self, upstream: httpx.Response, model: str
    ) -> Dict[str, Any]:
        """Process non-streaming text completion response."""
        created = int(time.time())
        response_id = "cmpl"
        full_text = ""

        try:
            async for raw_line in upstream.aiter_lines():
                if not raw_line:
                    continue
                line = raw_line.strip()
                if not line.startswith("data: "):
                    continue
                data = line[len("data: ") :].strip()
                if not data or data == "[DONE]":
                    if data == "[DONE]":
                        break
                    continue

                try:
                    evt = json.loads(data)
                except Exception:
                    continue

                if isinstance(evt.get("response"), dict) and isinstance(
                    evt["response"].get("id"), str
                ):
                    response_id = evt["response"].get("id") or response_id

                kind = evt.get("type")
                if kind == "response.output_text.delta":
                    full_text += evt.get("delta") or ""
                elif kind == "response.completed":
                    break
        finally:
            await upstream.aclose()

        return {
            "id": response_id,
            "object": "text_completion",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "text": full_text, "finish_reason": "stop", "logprobs": None}],
        }

    async def stream_chat_completion(
        self, upstream: httpx.Response, model: str, reasoning_compat: str = "think-tags"
    ):
        """Stream chat completion response."""
        created = int(time.time())
        response_id = "chatcmpl-stream"
        compat = (reasoning_compat or "think-tags").strip().lower()
        think_open = False
        think_closed = False

        try:
            async for raw_line in upstream.aiter_lines():
                if not raw_line:
                    continue
                line = raw_line.strip()
                if not line.startswith("data: "):
                    continue
                data = line[len("data: ") :].strip()
                if not data:
                    continue
                if data == "[DONE]":
                    break

                try:
                    evt = json.loads(data)
                except Exception:
                    continue

                kind = evt.get("type")
                if isinstance(evt.get("response"), dict) and isinstance(
                    evt["response"].get("id"), str
                ):
                    response_id = evt["response"].get("id") or response_id

                if kind == "response.output_text.delta":
                    delta_text = evt.get("delta") or ""

                    # Handle reasoning compatibility
                    if compat == "think-tags" and delta_text:
                        if "<think>" in delta_text and not think_open:
                            think_open = True
                        if "</think>" in delta_text and think_open:
                            think_closed = True

                    chunk = {
                        "id": response_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": delta_text},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"

                elif kind == "response.output_item.done":
                    item = evt.get("item") or {}
                    if isinstance(item, dict) and item.get("type") == "function_call":
                        call_id = item.get("call_id") or item.get("id") or ""
                        name = item.get("name") or ""
                        args = item.get("arguments") or ""
                        if (
                            isinstance(call_id, str)
                            and isinstance(name, str)
                            and isinstance(args, str)
                        ):
                            delta_chunk = {
                                "id": response_id,
                                "object": "chat.completion.chunk",
                                "created": created,
                                "model": model,
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {
                                            "tool_calls": [
                                                {
                                                    "index": 0,
                                                    "id": call_id,
                                                    "type": "function",
                                                    "function": {"name": name, "arguments": args},
                                                }
                                            ]
                                        },
                                        "finish_reason": None,
                                    }
                                ],
                            }
                            yield f"data: {json.dumps(delta_chunk)}\n\n"

                elif kind == "response.failed":
                    err = evt.get("response", {}).get("error", {}).get("message", "response.failed")
                    chunk = {"error": {"message": err}}
                    yield f"data: {json.dumps(chunk)}\n\n"

                elif kind == "response.completed":
                    if compat == "think-tags" and think_open and not think_closed:
                        close_chunk = {
                            "id": response_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": "</think>"},
                                    "finish_reason": None,
                                }
                            ],
                        }
                        yield f"data: {json.dumps(close_chunk)}\n\n"

                    # Send final chunk
                    final_chunk = {
                        "id": response_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                    }
                    yield f"data: {json.dumps(final_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                    break
        finally:
            await upstream.aclose()

    async def stream_text_completion(self, upstream: httpx.Response, model: str):
        """Stream text completion response."""
        created = int(time.time())
        response_id = "cmpl-stream"

        try:
            async for raw_line in upstream.aiter_lines():
                if not raw_line:
                    continue
                line = raw_line.strip()
                if not line.startswith("data: "):
                    continue
                data = line[len("data: ") :].strip()
                if not data or data == "[DONE]":
                    if data == "[DONE]":
                        chunk = {
                            "id": response_id,
                            "object": "text_completion.chunk",
                            "created": created,
                            "model": model,
                            "choices": [{"index": 0, "text": "", "finish_reason": "stop"}],
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                    continue

                try:
                    evt = json.loads(data)
                except Exception:
                    continue

                kind = evt.get("type")
                if isinstance(evt.get("response"), dict) and isinstance(
                    evt["response"].get("id"), str
                ):
                    response_id = evt["response"].get("id") or response_id

                if kind == "response.output_text.delta":
                    delta_text = evt.get("delta") or ""
                    chunk = {
                        "id": response_id,
                        "object": "text_completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{"index": 0, "text": delta_text, "finish_reason": None}],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"

                elif kind == "response.output_text.done":
                    chunk = {
                        "id": response_id,
                        "object": "text_completion.chunk",
                        "created": created,
                        "model": model,
                        "choices": [{"index": 0, "text": "", "finish_reason": "stop"}],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"

                elif kind == "response.completed":
                    yield "data: [DONE]\n\n"
                    break
        finally:
            await upstream.aclose()
