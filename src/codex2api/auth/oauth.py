"""
OAuth authentication implementation for Codex2API.

This module handles the OAuth 2.0 + PKCE flow for OpenAI authentication,
including authorization URL generation and token exchange.
"""

from __future__ import annotations

import time
import webbrowser
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode, urlparse, parse_qs

import httpx

from ..core import (
    get_logger,
    get_settings,
    AuthenticationError,
    TokenError,
    generate_pkce_codes,
    generate_state,
    generate_nonce,
    log_auth_event,
)
from ..models import TokenData, PkceCodes


class OAuthClient:
    """OAuth client for OpenAI authentication."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        self.auth_config = self.settings.auth
        
        # OAuth endpoints
        self.auth_url = "https://auth0.openai.com/authorize"
        self.token_url = "https://auth0.openai.com/oauth/token"
        self.userinfo_url = "https://auth0.openai.com/userinfo"
        
        # HTTP client
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={"User-Agent": f"{self.settings.app_name}/{self.settings.app_version}"}
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
    
    def generate_auth_url(self, no_browser: bool = False) -> Tuple[str, PkceCodes, str]:
        """
        Generate OAuth authorization URL with PKCE.
        
        Args:
            no_browser: If True, don't automatically open browser
            
        Returns:
            Tuple of (auth_url, pkce_codes, state)
        """
        # Generate PKCE codes
        code_verifier, code_challenge = generate_pkce_codes()
        pkce_codes = PkceCodes(
            code_verifier=code_verifier,
            code_challenge=code_challenge
        )
        
        # Generate state and nonce
        state = generate_state()
        nonce = generate_nonce()
        
        # Build authorization URL
        params = {
            "client_id": self.auth_config.client_id,
            "response_type": "code",
            "redirect_uri": self.auth_config.redirect_uri,
            "scope": self.auth_config.scope,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "login"
        }
        
        auth_url = f"{self.auth_url}?{urlencode(params)}"
        
        # Log auth event
        log_auth_event(
            self.logger,
            "auth_url_generated",
            success=True,
            details={"no_browser": no_browser}
        )
        
        # Open browser if requested
        if not no_browser:
            try:
                webbrowser.open(auth_url)
                self.logger.info("Browser opened for authentication")
            except Exception as e:
                self.logger.warning("Failed to open browser", error=str(e))
        
        return auth_url, pkce_codes, state
    
    async def exchange_code_for_tokens(
        self,
        authorization_code: str,
        pkce_codes: PkceCodes,
        state: str,
        received_state: str
    ) -> TokenData:
        """
        Exchange authorization code for tokens.
        
        Args:
            authorization_code: Authorization code from callback
            pkce_codes: PKCE codes used in authorization
            state: Original state parameter
            received_state: State parameter from callback
            
        Returns:
            Token data
            
        Raises:
            AuthenticationError: If token exchange fails
        """
        # Verify state parameter
        if state != received_state:
            raise AuthenticationError(
                "Invalid state parameter",
                error_code="invalid_state",
                details={"expected": state, "received": received_state}
            )
        
        # Prepare token request
        data = {
            "grant_type": "authorization_code",
            "client_id": self.auth_config.client_id,
            "code": authorization_code,
            "redirect_uri": self.auth_config.redirect_uri,
            "code_verifier": pkce_codes.code_verifier
        }
        
        try:
            # Make token request
            response = await self.client.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                raise AuthenticationError(
                    f"Token exchange failed: {response.status_code}",
                    error_code="token_exchange_failed",
                    details={"status_code": response.status_code, "error": error_data}
                )
            
            token_response = response.json()
            
            # Extract tokens
            token_data = TokenData(
                id_token=token_response["id_token"],
                access_token=token_response["access_token"],
                refresh_token=token_response.get("refresh_token", ""),
                account_id=""  # Will be populated from user info
            )
            
            # Get user info to populate account_id
            user_info = await self.get_user_info(token_data.access_token)
            token_data.account_id = user_info.get("sub", "")
            
            log_auth_event(
                self.logger,
                "token_exchange_success",
                user_id=token_data.account_id,
                success=True
            )
            
            return token_data
            
        except httpx.RequestError as e:
            raise AuthenticationError(
                f"Network error during token exchange: {str(e)}",
                error_code="network_error"
            )
        except Exception as e:
            log_auth_event(
                self.logger,
                "token_exchange_failed",
                success=False,
                details={"error": str(e)}
            )
            raise AuthenticationError(
                f"Token exchange failed: {str(e)}",
                error_code="token_exchange_failed"
            )
    
    async def refresh_tokens(self, refresh_token: str) -> TokenData:
        """
        Refresh access tokens using refresh token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            New token data
            
        Raises:
            TokenError: If refresh fails
        """
        data = {
            "grant_type": "refresh_token",
            "client_id": self.auth_config.client_id,
            "refresh_token": refresh_token
        }
        
        try:
            response = await self.client.post(
                self.token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                raise TokenError(
                    f"Token refresh failed: {response.status_code}",
                    error_code="token_refresh_failed",
                    details={"status_code": response.status_code, "error": error_data}
                )
            
            token_response = response.json()
            
            # Create new token data
            token_data = TokenData(
                id_token=token_response["id_token"],
                access_token=token_response["access_token"],
                refresh_token=token_response.get("refresh_token", refresh_token),  # Use new or keep old
                account_id=""  # Will be populated from user info
            )
            
            # Get user info
            user_info = await self.get_user_info(token_data.access_token)
            token_data.account_id = user_info.get("sub", "")
            
            log_auth_event(
                self.logger,
                "token_refresh_success",
                user_id=token_data.account_id,
                success=True
            )
            
            return token_data
            
        except httpx.RequestError as e:
            raise TokenError(
                f"Network error during token refresh: {str(e)}",
                error_code="network_error"
            )
        except Exception as e:
            log_auth_event(
                self.logger,
                "token_refresh_failed",
                success=False,
                details={"error": str(e)}
            )
            raise TokenError(
                f"Token refresh failed: {str(e)}",
                error_code="token_refresh_failed"
            )
    
    async def get_user_info(self, access_token: str) -> Dict[str, any]:
        """
        Get user information using access token.
        
        Args:
            access_token: Access token
            
        Returns:
            User information dictionary
            
        Raises:
            AuthenticationError: If request fails
        """
        try:
            response = await self.client.get(
                self.userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if response.status_code != 200:
                raise AuthenticationError(
                    f"Failed to get user info: {response.status_code}",
                    error_code="userinfo_failed"
                )
            
            return response.json()
            
        except httpx.RequestError as e:
            raise AuthenticationError(
                f"Network error getting user info: {str(e)}",
                error_code="network_error"
            )
    
    def parse_callback_url(self, callback_url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Parse OAuth callback URL to extract code, state, and error.
        
        Args:
            callback_url: Full callback URL
            
        Returns:
            Tuple of (code, state, error)
        """
        try:
            parsed = urlparse(callback_url)
            params = parse_qs(parsed.query)
            
            code = params.get("code", [None])[0]
            state = params.get("state", [None])[0]
            error = params.get("error", [None])[0]
            
            return code, state, error
            
        except Exception as e:
            self.logger.error("Failed to parse callback URL", error=str(e))
            return None, None, "invalid_callback_url"
