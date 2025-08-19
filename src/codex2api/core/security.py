"""
Security utilities for Codex2API.

This module provides security-related functions including PKCE implementation,
token validation, and security headers.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import time
from typing import Dict, Optional, Tuple

from .exceptions import TokenError, ValidationError


def generate_pkce_codes() -> Tuple[str, str]:
    """
    Generate PKCE code verifier and challenge.
    
    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    # Generate code verifier (43-128 characters)
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    
    # Generate code challenge (SHA256 hash of verifier)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    
    return code_verifier, code_challenge


def verify_pkce_challenge(code_verifier: str, code_challenge: str) -> bool:
    """
    Verify PKCE code challenge against verifier.
    
    Args:
        code_verifier: The original code verifier
        code_challenge: The code challenge to verify
        
    Returns:
        True if challenge matches verifier
    """
    try:
        expected_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        return secrets.compare_digest(code_challenge, expected_challenge)
    except Exception:
        return False


def generate_state() -> str:
    """
    Generate a secure random state parameter for OAuth.
    
    Returns:
        Random state string
    """
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')


def generate_nonce() -> str:
    """
    Generate a secure random nonce for OpenID Connect.
    
    Returns:
        Random nonce string
    """
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')


def generate_session_id() -> str:
    """
    Generate a secure session ID.
    
    Returns:
        Random session ID string
    """
    return secrets.token_urlsafe(32)


def generate_request_id() -> str:
    """
    Generate a unique request ID for tracing.
    
    Returns:
        Random request ID string
    """
    return secrets.token_urlsafe(16)


def hash_token(token: str) -> str:
    """
    Hash a token for secure storage.
    
    Args:
        token: Token to hash
        
    Returns:
        SHA256 hash of the token
    """
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def verify_token_hash(token: str, token_hash: str) -> bool:
    """
    Verify a token against its hash.
    
    Args:
        token: Token to verify
        token_hash: Expected hash
        
    Returns:
        True if token matches hash
    """
    return secrets.compare_digest(hash_token(token), token_hash)


def is_token_expired(expires_at: int, buffer_seconds: int = 300) -> bool:
    """
    Check if a token is expired or will expire soon.
    
    Args:
        expires_at: Token expiration timestamp
        buffer_seconds: Buffer time before expiration
        
    Returns:
        True if token is expired or will expire within buffer
    """
    return time.time() >= (expires_at - buffer_seconds)


def validate_bearer_token(authorization_header: Optional[str]) -> str:
    """
    Extract and validate bearer token from Authorization header.
    
    Args:
        authorization_header: Authorization header value
        
    Returns:
        Extracted token
        
    Raises:
        TokenError: If token is invalid or missing
    """
    if not authorization_header:
        raise TokenError("Missing Authorization header")
    
    parts = authorization_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise TokenError("Invalid Authorization header format")
    
    token = parts[1]
    if not token:
        raise TokenError("Empty bearer token")
    
    return token


def sanitize_user_input(input_str: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        input_str: Input string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
        
    Raises:
        ValidationError: If input is too long
    """
    if len(input_str) > max_length:
        raise ValidationError(f"Input too long (max {max_length} characters)")
    
    # Remove null bytes and control characters
    sanitized = ''.join(char for char in input_str if ord(char) >= 32 or char in '\t\n\r')
    
    return sanitized.strip()


def get_security_headers() -> Dict[str, str]:
    """
    Get security headers for HTTP responses.
    
    Returns:
        Dictionary of security headers
    """
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": "default-src 'self'",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
    }


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive data for logging.
    
    Args:
        data: Sensitive data to mask
        visible_chars: Number of characters to show at the end
        
    Returns:
        Masked string
    """
    if len(data) <= visible_chars:
        return "*" * len(data)
    
    return "*" * (len(data) - visible_chars) + data[-visible_chars:]


def validate_ip_address(ip: str) -> bool:
    """
    Validate IP address format.
    
    Args:
        ip: IP address to validate
        
    Returns:
        True if valid IP address
    """
    import ipaddress
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def is_safe_redirect_url(url: str, allowed_hosts: list[str]) -> bool:
    """
    Check if a redirect URL is safe.
    
    Args:
        url: URL to check
        allowed_hosts: List of allowed host names
        
    Returns:
        True if URL is safe for redirect
    """
    from urllib.parse import urlparse
    
    try:
        parsed = urlparse(url)
        
        # Must be HTTPS (except localhost for development)
        if parsed.scheme not in ('https', 'http'):
            return False
        
        if parsed.scheme == 'http' and parsed.hostname not in ('localhost', '127.0.0.1'):
            return False
        
        # Must be in allowed hosts
        if parsed.hostname not in allowed_hosts:
            return False
        
        return True
    except Exception:
        return False


def rate_limit_key(ip: str, endpoint: str) -> str:
    """
    Generate a rate limit key for an IP and endpoint.
    
    Args:
        ip: Client IP address
        endpoint: API endpoint
        
    Returns:
        Rate limit key
    """
    return f"rate_limit:{ip}:{endpoint}"


def generate_api_key() -> str:
    """
    Generate a secure API key.
    
    Returns:
        Random API key string
    """
    return f"sk-{secrets.token_urlsafe(32)}"


class SecurityContext:
    """Security context for request processing."""
    
    def __init__(
        self,
        client_ip: str,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        self.client_ip = client_ip
        self.user_agent = user_agent
        self.request_id = request_id or generate_request_id()
        self.authenticated = False
        self.user_id: Optional[str] = None
        self.permissions: set[str] = set()
    
    def authenticate(self, user_id: str, permissions: Optional[set[str]] = None) -> None:
        """Mark context as authenticated."""
        self.authenticated = True
        self.user_id = user_id
        self.permissions = permissions or set()
    
    def has_permission(self, permission: str) -> bool:
        """Check if context has a specific permission."""
        return self.authenticated and permission in self.permissions
    
    def to_dict(self) -> Dict[str, any]:
        """Convert context to dictionary."""
        return {
            "client_ip": self.client_ip,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "authenticated": self.authenticated,
            "user_id": self.user_id,
            "permissions": list(self.permissions)
        }
