"""
Configuration management for Codex2API.

This module handles all application configuration using Pydantic Settings
for environment variable management and validation.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="DB_",
        case_sensitive=False,
        extra="forbid"
    )
    
    # SQLite settings for token storage
    url: str = Field(
        default="sqlite:///./data/codex2api.db",
        description="Database URL for token storage"
    )
    echo: bool = Field(
        default=False,
        description="Enable SQL query logging"
    )
    pool_size: int = Field(
        default=5,
        description="Database connection pool size",
        ge=1,
        le=20
    )


class AuthConfig(BaseSettings):
    """Authentication configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        case_sensitive=False,
        extra="forbid"
    )
    
    # OAuth settings
    client_id: str = Field(
        default="pdlLIX2Y72MIl2rhLhTE9VV9bN905kBh",
        description="OpenAI OAuth client ID"
    )
    redirect_uri: str = Field(
        default="http://localhost:3000/api/auth/callback/openai",
        description="OAuth redirect URI"
    )
    scope: str = Field(
        default="openid email profile offline_access model.request model.read organization.read",
        description="OAuth scope"
    )
    
    # Token settings
    token_refresh_threshold: int = Field(
        default=300,
        description="Seconds before expiry to refresh token",
        ge=60,
        le=3600
    )
    max_refresh_attempts: int = Field(
        default=3,
        description="Maximum token refresh attempts",
        ge=1,
        le=10
    )
    
    # Session settings
    session_timeout: int = Field(
        default=3600,
        description="Session timeout in seconds",
        ge=300,
        le=86400
    )


class ServerConfig(BaseSettings):
    """Server configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="SERVER_",
        case_sensitive=False,
        extra="forbid"
    )
    
    host: str = Field(
        default="0.0.0.0",
        description="Server host address"
    )
    port: int = Field(
        default=8000,
        description="Server port",
        ge=1,
        le=65535
    )
    workers: int = Field(
        default=1,
        description="Number of worker processes",
        ge=1,
        le=16
    )
    reload: bool = Field(
        default=False,
        description="Enable auto-reload in development"
    )
    
    # CORS settings
    cors_origins: List[str] = Field(
        default=["*"],
        description="Allowed CORS origins"
    )
    cors_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="Allowed CORS methods"
    )
    cors_headers: List[str] = Field(
        default=["*"],
        description="Allowed CORS headers"
    )


class LoggingConfig(BaseSettings):
    """Logging configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        case_sensitive=False,
        extra="forbid"
    )
    
    level: str = Field(
        default="INFO",
        description="Logging level"
    )
    format: str = Field(
        default="json",
        description="Log format (json or text)"
    )
    file_path: Optional[str] = Field(
        default=None,
        description="Log file path (optional)"
    )
    max_file_size: int = Field(
        default=10485760,  # 10MB
        description="Maximum log file size in bytes",
        ge=1048576,  # 1MB
        le=104857600  # 100MB
    )
    backup_count: int = Field(
        default=5,
        description="Number of backup log files",
        ge=1,
        le=20
    )
    
    @validator("level")
    def validate_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()
    
    @validator("format")
    def validate_format(cls, v: str) -> str:
        """Validate log format."""
        valid_formats = {"json", "text"}
        if v.lower() not in valid_formats:
            raise ValueError(f"Invalid log format: {v}. Must be one of {valid_formats}")
        return v.lower()


class APIConfig(BaseSettings):
    """API configuration settings."""
    
    model_config = SettingsConfigDict(
        env_prefix="API_",
        case_sensitive=False,
        extra="forbid"
    )
    
    # Rate limiting
    rate_limit_requests: int = Field(
        default=100,
        description="Requests per minute per IP",
        ge=1,
        le=10000
    )
    rate_limit_window: int = Field(
        default=60,
        description="Rate limit window in seconds",
        ge=1,
        le=3600
    )
    
    # Request limits
    max_request_size: int = Field(
        default=1048576,  # 1MB
        description="Maximum request size in bytes",
        ge=1024,  # 1KB
        le=10485760  # 10MB
    )
    request_timeout: int = Field(
        default=30,
        description="Request timeout in seconds",
        ge=1,
        le=300
    )
    
    # OpenAI API settings
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API base URL"
    )
    openai_timeout: int = Field(
        default=60,
        description="OpenAI API timeout in seconds",
        ge=5,
        le=300
    )


class Settings(BaseSettings):
    """Main application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid"
    )
    
    # Application info
    app_name: str = Field(
        default="Codex2API",
        description="Application name"
    )
    app_version: str = Field(
        default="0.2.0",
        description="Application version"
    )
    app_description: str = Field(
        default="Modern OpenAI compatible API powered by ChatGPT",
        description="Application description"
    )
    
    # Environment
    environment: str = Field(
        default="development",
        description="Application environment"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    # Data directory
    data_dir: Path = Field(
        default=Path("./data"),
        description="Data directory path"
    )
    
    # Sub-configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    
    @validator("environment")
    def validate_environment(cls, v: str) -> str:
        """Validate environment."""
        valid_envs = {"development", "staging", "production", "testing"}
        if v.lower() not in valid_envs:
            raise ValueError(f"Invalid environment: {v}. Must be one of {valid_envs}")
        return v.lower()
    
    @validator("data_dir")
    def validate_data_dir(cls, v: Path) -> Path:
        """Ensure data directory exists."""
        v.mkdir(parents=True, exist_ok=True)
        return v
    
    def model_post_init(self, __context: Any) -> None:
        """Post-initialization setup."""
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.data_dir / "logs").mkdir(exist_ok=True)
        (self.data_dir / "cache").mkdir(exist_ok=True)
        (self.data_dir / "sessions").mkdir(exist_ok=True)


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global settings
    settings = Settings()
    return settings
