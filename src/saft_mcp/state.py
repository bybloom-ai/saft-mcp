"""Session state management for the SAF-T MCP server."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from saft_mcp.config import settings
from saft_mcp.exceptions import SaftError

if TYPE_CHECKING:
    from saft_mcp.parser.models import FileMetadata, SaftData


@dataclass
class SessionState:
    loaded_file: SaftData | None = None
    file_metadata: FileMetadata | None = None
    file_path: str | None = None
    parse_mode: str = "full"  # "full" or "streaming"
    last_accessed: float = field(default_factory=time.monotonic)
    estimated_memory_bytes: int = 0


class SessionStore:
    """Async-safe session store with TTL-based eviction."""

    def __init__(
        self,
        timeout_seconds: int = settings.session_timeout_seconds,
        max_sessions: int = settings.max_concurrent_sessions,
    ):
        self._sessions: dict[str, SessionState] = {}
        self._lock = asyncio.Lock()
        self._timeout = timeout_seconds
        self._max_sessions = max_sessions

    async def get(self, session_id: str) -> SessionState:
        async with self._lock:
            self._evict_expired()
            if session_id not in self._sessions:
                if len(self._sessions) >= self._max_sessions:
                    raise SaftError(
                        f"Maximum concurrent sessions ({self._max_sessions}) reached. "
                        "Try again later."
                    )
                self._sessions[session_id] = SessionState()
            session = self._sessions[session_id]
            session.last_accessed = time.monotonic()
            return session

    async def remove(self, session_id: str) -> None:
        async with self._lock:
            self._sessions.pop(session_id, None)

    def _evict_expired(self) -> None:
        now = time.monotonic()
        expired = [
            sid
            for sid, s in self._sessions.items()
            if now - s.last_accessed > self._timeout
        ]
        for sid in expired:
            del self._sessions[sid]


# Global session store
session_store = SessionStore()
