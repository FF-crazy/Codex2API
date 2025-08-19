"""
HTTP client utilities for Codex2API.

This module provides a configured HTTP client with retry logic,
timeout handling, and request/response logging.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional, Union

import httpx
from httpx import Response

from ..core import (
    get_logger,
    get_settings,
    APIError,
    TimeoutError,
    log_api_call,
    log_error,
)


class HTTPClient:
    """Enhanced HTTP client with retry logic and logging."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.settings = get_settings()
        self.logger = get_logger(__name__)

        # Client configuration
        self.base_url = base_url
        self.timeout = timeout or self.settings.api.openai_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Default headers
        default_headers = {
            "User-Agent": f"{self.settings.app_name}/{self.settings.app_version}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if headers:
            default_headers.update(headers)

        # Create HTTP client
        client_kwargs = {
            "timeout": httpx.Timeout(self.timeout),
            "headers": default_headers,
            "follow_redirects": True,
        }
        if base_url:
            client_kwargs["base_url"] = base_url

        self.client = httpx.AsyncClient(**client_kwargs)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
        files: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        retry_on_status: Optional[set[int]] = None,
    ) -> Response:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method
            url: Request URL
            headers: Additional headers
            params: Query parameters
            json: JSON data
            data: Raw data
            files: File uploads
            stream: Whether to stream response
            retry_on_status: Status codes to retry on

        Returns:
            HTTP response

        Raises:
            APIError: If request fails after retries
            TimeoutError: If request times out
        """
        retry_on_status = retry_on_status or {429, 500, 502, 503, 504}
        start_time = time.time()
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                # Make request
                response = await self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json,
                    data=data,
                    files=files,
                )

                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000

                # Log API call
                log_api_call(
                    self.logger,
                    service=self.base_url or "unknown",
                    endpoint=url,
                    method=method,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    request_size=self._get_request_size(json, data),
                    response_size=len(response.content) if hasattr(response, "content") else None,
                )

                # Check if we should retry
                if attempt < self.max_retries and response.status_code in retry_on_status:
                    self.logger.warning(
                        "Request failed, retrying",
                        attempt=attempt + 1,
                        status_code=response.status_code,
                        url=url,
                    )

                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    continue

                return response

            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self.max_retries:
                    self.logger.warning("Request timeout, retrying", attempt=attempt + 1, url=url)
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    continue
                else:
                    raise TimeoutError(
                        f"Request timed out after {self.max_retries} retries",
                        details={"url": url, "timeout": self.timeout},
                    )

            except httpx.RequestError as e:
                last_exception = e
                if attempt < self.max_retries:
                    self.logger.warning(
                        "Request error, retrying", attempt=attempt + 1, error=str(e), url=url
                    )
                    await asyncio.sleep(self.retry_delay * (2**attempt))
                    continue
                else:
                    raise APIError(
                        f"Request failed after {self.max_retries} retries: {str(e)}",
                        details={"url": url, "error": str(e)},
                    )

        # This should never be reached, but just in case
        if last_exception:
            raise APIError(f"Request failed: {str(last_exception)}", details={"url": url})

    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """Make GET request."""
        return await self.request("GET", url, headers=headers, params=params)

    async def post(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
    ) -> Response:
        """Make POST request."""
        return await self.request("POST", url, headers=headers, json=json, data=data)

    async def put(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
    ) -> Response:
        """Make PUT request."""
        return await self.request("PUT", url, headers=headers, json=json, data=data)

    async def delete(self, url: str, headers: Optional[Dict[str, str]] = None) -> Response:
        """Make DELETE request."""
        return await self.request("DELETE", url, headers=headers)

    async def stream_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Union[str, bytes]] = None,
    ):
        """
        Make streaming HTTP request.

        Args:
            method: HTTP method
            url: Request URL
            headers: Additional headers
            params: Query parameters
            json: JSON data
            data: Raw data

        Yields:
            Response chunks
        """
        try:
            async with self.client.stream(
                method=method, url=url, headers=headers, params=params, json=json, data=data
            ) as response:
                # Log initial response
                self.logger.info(
                    "Streaming request started",
                    method=method,
                    url=url,
                    status_code=response.status_code,
                )

                # Check for errors
                if response.status_code >= 400:
                    error_content = await response.aread()
                    raise APIError(
                        f"Streaming request failed: {response.status_code}",
                        status_code=response.status_code,
                        details={"content": error_content.decode("utf-8", errors="ignore")},
                    )

                # Stream response
                async for chunk in response.aiter_bytes():
                    yield chunk

        except httpx.RequestError as e:
            log_error(self.logger, e, context={"method": method, "url": url})
            raise APIError(
                f"Streaming request failed: {str(e)}", details={"url": url, "error": str(e)}
            )

    def _get_request_size(
        self, json_data: Optional[Dict[str, Any]], raw_data: Optional[Union[str, bytes]]
    ) -> Optional[int]:
        """Calculate request size in bytes."""
        if json_data:
            import json

            return len(json.dumps(json_data).encode("utf-8"))
        elif raw_data:
            if isinstance(raw_data, str):
                return len(raw_data.encode("utf-8"))
            else:
                return len(raw_data)
        return None

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


class OpenAIHTTPClient(HTTPClient):
    """HTTP client specifically configured for OpenAI API."""

    def __init__(self, api_key: Optional[str] = None):
        self.settings = get_settings()

        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        super().__init__(
            base_url=self.settings.api.openai_base_url,
            timeout=self.settings.api.openai_timeout,
            headers=headers,
        )

    def set_api_key(self, api_key: str):
        """Update API key for requests."""
        self.client.headers["Authorization"] = f"Bearer {api_key}"


class ChatGPTHTTPClient(HTTPClient):
    """HTTP client specifically configured for ChatGPT API."""

    def __init__(self, access_token: Optional[str] = None):
        headers = {}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        super().__init__(base_url="https://chatgpt.com", headers=headers)

    def set_access_token(self, access_token: str):
        """Update access token for requests."""
        self.client.headers["Authorization"] = f"Bearer {access_token}"
