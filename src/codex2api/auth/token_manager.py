"""
Token management for Codex2API.

This module handles token storage, validation, and automatic refresh
with support for multiple authentication sessions.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import httpx

from ..core import (
    get_logger,
    get_settings,
    TokenError,
    TokenExpiredError,
    TokenRefreshError,
    is_token_expired,
    hash_token,
    log_auth_event,
)
from ..models import TokenData, AuthBundle
from .oauth import OAuthClient


class TokenManager:
    """Manages authentication tokens with automatic refresh."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.settings = get_settings()
        self.logger = get_logger(__name__)
        
        # Storage path for tokens
        if storage_path is None:
            storage_path = self.settings.data_dir / "auth.json"
        self.storage_path = storage_path
        
        # In-memory token cache
        self._token_cache: Dict[str, AuthBundle] = {}
        
        # OAuth client for token refresh
        self._oauth_client: Optional[OAuthClient] = None
    
    async def _get_oauth_client(self) -> OAuthClient:
        """Get or create OAuth client."""
        if self._oauth_client is None:
            self._oauth_client = OAuthClient()
        return self._oauth_client
    
    def store_tokens(
        self,
        token_data: TokenData,
        api_key: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> AuthBundle:
        """
        Store authentication tokens.
        
        Args:
            token_data: Token data to store
            api_key: Optional OpenAI API key
            user_id: User identifier (defaults to account_id)
            
        Returns:
            Auth bundle with stored tokens
        """
        user_id = user_id or token_data.account_id
        
        # Create auth bundle
        auth_bundle = AuthBundle(
            api_key=api_key,
            token_data=token_data,
            last_refresh=datetime.now(timezone.utc).isoformat()
        )
        
        # Store in cache
        self._token_cache[user_id] = auth_bundle
        
        # Persist to disk
        self._save_to_disk()
        
        log_auth_event(
            self.logger,
            "tokens_stored",
            user_id=user_id,
            success=True
        )
        
        return auth_bundle
    
    def get_tokens(self, user_id: str) -> Optional[AuthBundle]:
        """
        Get stored tokens for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Auth bundle if found, None otherwise
        """
        # Check cache first
        if user_id in self._token_cache:
            return self._token_cache[user_id]
        
        # Load from disk
        self._load_from_disk()
        
        return self._token_cache.get(user_id)
    
    async def get_valid_tokens(self, user_id: str, force_refresh: bool = False) -> Optional[AuthBundle]:
        """
        Get valid tokens for a user, refreshing if necessary.
        
        Args:
            user_id: User identifier
            force_refresh: Force token refresh even if not expired
            
        Returns:
            Valid auth bundle or None if not available
            
        Raises:
            TokenRefreshError: If token refresh fails
        """
        auth_bundle = self.get_tokens(user_id)
        if not auth_bundle:
            return None
        
        # Check if tokens need refresh
        needs_refresh = force_refresh or self._needs_refresh(auth_bundle)
        
        if needs_refresh:
            try:
                auth_bundle = await self._refresh_tokens(user_id, auth_bundle)
            except Exception as e:
                self.logger.error(
                    "Failed to refresh tokens",
                    user_id=user_id,
                    error=str(e)
                )
                raise TokenRefreshError(
                    f"Failed to refresh tokens for user {user_id}",
                    details={"user_id": user_id, "error": str(e)}
                )
        
        return auth_bundle
    
    def _needs_refresh(self, auth_bundle: AuthBundle) -> bool:
        """
        Check if tokens need to be refreshed.
        
        Args:
            auth_bundle: Auth bundle to check
            
        Returns:
            True if tokens need refresh
        """
        try:
            # Parse the ID token to get expiration (simplified check)
            # In a real implementation, you'd decode the JWT properly
            # For now, we'll use a time-based heuristic
            
            last_refresh = datetime.fromisoformat(auth_bundle.last_refresh.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            
            # Refresh if tokens are older than threshold
            age_seconds = (now - last_refresh).total_seconds()
            threshold = self.settings.auth.token_refresh_threshold
            
            return age_seconds >= threshold
            
        except Exception as e:
            self.logger.warning("Error checking token expiration", error=str(e))
            return True  # Err on the side of caution
    
    async def _refresh_tokens(self, user_id: str, auth_bundle: AuthBundle) -> AuthBundle:
        """
        Refresh tokens for a user.
        
        Args:
            user_id: User identifier
            auth_bundle: Current auth bundle
            
        Returns:
            Updated auth bundle with new tokens
            
        Raises:
            TokenRefreshError: If refresh fails
        """
        oauth_client = await self._get_oauth_client()
        
        try:
            # Attempt token refresh
            new_token_data = await oauth_client.refresh_tokens(
                auth_bundle.token_data.refresh_token
            )
            
            # Create updated auth bundle
            updated_bundle = AuthBundle(
                api_key=auth_bundle.api_key,  # Keep existing API key
                token_data=new_token_data,
                last_refresh=datetime.now(timezone.utc).isoformat()
            )
            
            # Store updated tokens
            self._token_cache[user_id] = updated_bundle
            self._save_to_disk()
            
            log_auth_event(
                self.logger,
                "tokens_refreshed",
                user_id=user_id,
                success=True
            )
            
            return updated_bundle
            
        except Exception as e:
            log_auth_event(
                self.logger,
                "token_refresh_failed",
                user_id=user_id,
                success=False,
                details={"error": str(e)}
            )
            raise
    
    def revoke_tokens(self, user_id: str) -> bool:
        """
        Revoke and remove tokens for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if tokens were removed
        """
        if user_id in self._token_cache:
            del self._token_cache[user_id]
            self._save_to_disk()
            
            log_auth_event(
                self.logger,
                "tokens_revoked",
                user_id=user_id,
                success=True
            )
            
            return True
        
        return False
    
    def list_users(self) -> list[str]:
        """
        List all users with stored tokens.
        
        Returns:
            List of user IDs
        """
        self._load_from_disk()
        return list(self._token_cache.keys())
    
    def _save_to_disk(self) -> None:
        """Save token cache to disk."""
        try:
            # Ensure directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to serializable format
            data = {}
            for user_id, auth_bundle in self._token_cache.items():
                data[user_id] = auth_bundle.model_dump()
            
            # Write to file
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Set restrictive permissions
            self.storage_path.chmod(0o600)
            
        except Exception as e:
            self.logger.error("Failed to save tokens to disk", error=str(e))
    
    def _load_from_disk(self) -> None:
        """Load token cache from disk."""
        if not self.storage_path.exists():
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert from serialized format
            self._token_cache = {}
            for user_id, bundle_data in data.items():
                try:
                    auth_bundle = AuthBundle.model_validate(bundle_data)
                    self._token_cache[user_id] = auth_bundle
                except Exception as e:
                    self.logger.warning(
                        "Failed to load tokens for user",
                        user_id=user_id,
                        error=str(e)
                    )
            
        except Exception as e:
            self.logger.error("Failed to load tokens from disk", error=str(e))
    
    def cleanup_expired_tokens(self) -> int:
        """
        Remove expired tokens from storage.
        
        Returns:
            Number of expired token sets removed
        """
        self._load_from_disk()
        
        expired_users = []
        for user_id, auth_bundle in self._token_cache.items():
            if self._is_bundle_expired(auth_bundle):
                expired_users.append(user_id)
        
        # Remove expired tokens
        for user_id in expired_users:
            del self._token_cache[user_id]
            log_auth_event(
                self.logger,
                "expired_tokens_removed",
                user_id=user_id,
                success=True
            )
        
        if expired_users:
            self._save_to_disk()
        
        return len(expired_users)
    
    def _is_bundle_expired(self, auth_bundle: AuthBundle) -> bool:
        """
        Check if an auth bundle is completely expired.
        
        Args:
            auth_bundle: Auth bundle to check
            
        Returns:
            True if bundle is expired and cannot be refreshed
        """
        try:
            # Check if refresh token is present
            if not auth_bundle.token_data.refresh_token:
                return True
            
            # Check if bundle is very old (beyond refresh token lifetime)
            last_refresh = datetime.fromisoformat(auth_bundle.last_refresh.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            age_days = (now - last_refresh).days
            
            # Assume refresh tokens expire after 30 days
            return age_days > 30
            
        except Exception:
            return True  # Err on the side of caution


# Global token manager instance
_token_manager: Optional[TokenManager] = None


def get_token_manager() -> TokenManager:
    """Get the global token manager instance."""
    global _token_manager
    if _token_manager is None:
        _token_manager = TokenManager()
    return _token_manager
