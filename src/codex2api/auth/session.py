"""
Session management for Codex2API.

This module handles user sessions, authentication state, and session persistence
with support for multiple concurrent sessions.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Set

from pydantic import BaseModel, Field

from ..core import (
    get_logger,
    get_settings,
    AuthenticationError,
    generate_session_id,
    log_auth_event,
)
from ..models import AuthBundle


class SessionData(BaseModel):
    """Session data model."""

    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User identifier")
    created_at: datetime = Field(..., description="Session creation time")
    last_accessed: datetime = Field(..., description="Last access time")
    expires_at: datetime = Field(..., description="Session expiration time")
    client_ip: str = Field(..., description="Client IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")
    permissions: Set[str] = Field(default_factory=set, description="Session permissions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.now(timezone.utc) >= self.expires_at

    def is_valid(self) -> bool:
        """Check if session is valid (not expired)."""
        return not self.is_expired()

    def refresh(self, timeout_seconds: int) -> None:
        """Refresh session expiration."""
        now = datetime.now(timezone.utc)
        self.last_accessed = now
        self.expires_at = now + timedelta(seconds=timeout_seconds)


class SessionManager:
    """Manages user sessions with persistence and cleanup."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.settings = get_settings()
        self.logger = get_logger(__name__)

        # Storage path for sessions
        if storage_path is None:
            storage_path = self.settings.data_dir / "sessions" / "sessions.json"
        self.storage_path = storage_path

        # In-memory session cache
        self._sessions: Dict[str, SessionData] = {}

        # Load existing sessions
        self._load_from_disk()

    def create_session(
        self,
        user_id: str,
        client_ip: str,
        user_agent: Optional[str] = None,
        permissions: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionData:
        """
        Create a new user session.

        Args:
            user_id: User identifier
            client_ip: Client IP address
            user_agent: User agent string
            permissions: Session permissions
            metadata: Additional metadata

        Returns:
            Created session data
        """
        session_id = generate_session_id()
        now = datetime.now(timezone.utc)
        timeout = self.settings.auth.session_timeout

        session_data = SessionData(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            last_accessed=now,
            expires_at=now + timedelta(seconds=timeout),
            client_ip=client_ip,
            user_agent=user_agent,
            permissions=permissions or set(),
            metadata=metadata or {},
        )

        # Store session
        self._sessions[session_id] = session_data
        self._save_to_disk()

        log_auth_event(
            self.logger,
            "session_created",
            user_id=user_id,
            success=True,
            details={
                "session_id": session_id,
                "client_ip": client_ip,
                "expires_at": session_data.expires_at.isoformat(),
            },
        )

        return session_data

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session data if found and valid, None otherwise
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Check if session is expired
        if session.is_expired():
            self.delete_session(session_id)
            return None

        return session

    def refresh_session(self, session_id: str) -> bool:
        """
        Refresh session expiration.

        Args:
            session_id: Session identifier

        Returns:
            True if session was refreshed
        """
        session = self.get_session(session_id)
        if not session:
            return False

        # Refresh session
        session.refresh(self.settings.auth.session_timeout)
        self._save_to_disk()

        log_auth_event(
            self.logger,
            "session_refreshed",
            user_id=session.user_id,
            success=True,
            details={"session_id": session_id, "expires_at": session.expires_at.isoformat()},
        )

        return True

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted
        """
        session = self._sessions.pop(session_id, None)
        if session:
            self._save_to_disk()

            log_auth_event(
                self.logger,
                "session_deleted",
                user_id=session.user_id,
                success=True,
                details={"session_id": session_id},
            )

            return True

        return False

    def delete_user_sessions(self, user_id: str) -> int:
        """
        Delete all sessions for a user.

        Args:
            user_id: User identifier

        Returns:
            Number of sessions deleted
        """
        sessions_to_delete = [
            session_id
            for session_id, session in self._sessions.items()
            if session.user_id == user_id
        ]

        for session_id in sessions_to_delete:
            del self._sessions[session_id]

        if sessions_to_delete:
            self._save_to_disk()

            log_auth_event(
                self.logger,
                "user_sessions_deleted",
                user_id=user_id,
                success=True,
                details={"sessions_deleted": len(sessions_to_delete)},
            )

        return len(sessions_to_delete)

    def get_user_sessions(self, user_id: str) -> list[SessionData]:
        """
        Get all active sessions for a user.

        Args:
            user_id: User identifier

        Returns:
            List of active sessions
        """
        sessions = []
        for session in self._sessions.values():
            if session.user_id == user_id and session.is_valid():
                sessions.append(session)

        return sessions

    def validate_session(
        self, session_id: str, client_ip: str, required_permissions: Optional[Set[str]] = None
    ) -> Optional[SessionData]:
        """
        Validate a session with additional checks.

        Args:
            session_id: Session identifier
            client_ip: Client IP address
            required_permissions: Required permissions

        Returns:
            Session data if valid, None otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return None

        # Check IP address (optional strict mode)
        if self.settings.environment == "production":
            if session.client_ip != client_ip:
                self.logger.warning(
                    "Session IP mismatch",
                    session_id=session_id,
                    expected_ip=session.client_ip,
                    actual_ip=client_ip,
                )
                # In production, you might want to invalidate the session
                # For now, we'll just log the warning

        # Check permissions
        if required_permissions:
            if not required_permissions.issubset(session.permissions):
                return None

        # Refresh session on successful validation
        self.refresh_session(session_id)

        return session

    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions.

        Returns:
            Number of expired sessions removed
        """
        expired_sessions = [
            session_id for session_id, session in self._sessions.items() if session.is_expired()
        ]

        for session_id in expired_sessions:
            session = self._sessions.pop(session_id)
            log_auth_event(
                self.logger,
                "expired_session_removed",
                user_id=session.user_id,
                success=True,
                details={"session_id": session_id},
            )

        if expired_sessions:
            self._save_to_disk()

        return len(expired_sessions)

    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get session statistics.

        Returns:
            Dictionary with session statistics
        """
        now = datetime.now(timezone.utc)
        active_sessions = [s for s in self._sessions.values() if s.is_valid()]

        return {
            "total_sessions": len(self._sessions),
            "active_sessions": len(active_sessions),
            "expired_sessions": len(self._sessions) - len(active_sessions),
            "unique_users": len(set(s.user_id for s in active_sessions)),
            "oldest_session": min((s.created_at for s in active_sessions), default=now).isoformat(),
            "newest_session": max((s.created_at for s in active_sessions), default=now).isoformat(),
        }

    def _save_to_disk(self) -> None:
        """Save sessions to disk."""
        try:
            # Ensure directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert to serializable format
            data = {}
            for session_id, session in self._sessions.items():
                session_dict = session.model_dump()
                # Convert datetime objects to ISO strings
                session_dict["created_at"] = session.created_at.isoformat()
                session_dict["last_accessed"] = session.last_accessed.isoformat()
                session_dict["expires_at"] = session.expires_at.isoformat()
                # Convert set to list
                session_dict["permissions"] = list(session.permissions)
                data[session_id] = session_dict

            # Write to file
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Set restrictive permissions
            self.storage_path.chmod(0o600)

        except Exception as e:
            self.logger.error("Failed to save sessions to disk", error=str(e))

    def _load_from_disk(self) -> None:
        """Load sessions from disk."""
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Convert from serialized format
            self._sessions = {}
            for session_id, session_dict in data.items():
                try:
                    # Convert ISO strings back to datetime objects
                    session_dict["created_at"] = datetime.fromisoformat(session_dict["created_at"])
                    session_dict["last_accessed"] = datetime.fromisoformat(
                        session_dict["last_accessed"]
                    )
                    session_dict["expires_at"] = datetime.fromisoformat(session_dict["expires_at"])
                    # Convert list back to set
                    session_dict["permissions"] = set(session_dict["permissions"])

                    session = SessionData(**session_dict)
                    self._sessions[session_id] = session
                except Exception as e:
                    self.logger.warning(
                        "Failed to load session", session_id=session_id, error=str(e)
                    )

        except Exception as e:
            self.logger.error("Failed to load sessions from disk", error=str(e))


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
