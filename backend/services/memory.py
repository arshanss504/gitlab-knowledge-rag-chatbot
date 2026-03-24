"""
app/services/memory.py
Conversation memory — Redis if available, otherwise simple dict.
"""

import json
from typing import Optional

from backend.core.config import CONVERSATION_MAX_TURNS, CONVERSATION_TTL_SECONDS, get_settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


class ConversationMemory:
    def __init__(self):
        self._max_items = CONVERSATION_MAX_TURNS * 2
        self._ttl = CONVERSATION_TTL_SECONDS
        self._redis = None
        self._store: dict[str, list[dict]] = {}

        redis_url = get_settings().redis_url
        if redis_url:
            try:
                import redis as redis_lib

                self._redis = redis_lib.from_url(redis_url, decode_responses=True)
                self._redis.ping()
                logger.info("Redis memory backend connected", url=redis_url)
            except Exception as e:
                logger.warning("Redis unavailable, using in-memory fallback", error=str(e))
                self._redis = None

    def add_user_turn(self, session_id: str, content: str) -> None:
        self._append(session_id, {"role": "user", "content": content})

    def add_assistant_turn(self, session_id: str, content: str) -> None:
        self._append(session_id, {"role": "assistant", "content": content})

    def _append(self, session_id: str, turn: dict) -> None:
        if self._redis:
            key = f"rag:conv:{session_id}"
            self._redis.rpush(key, json.dumps(turn))
            self._redis.ltrim(key, -self._max_items, -1)
            self._redis.expire(key, self._ttl)
        else:
            if session_id not in self._store:
                self._store[session_id] = []
            self._store[session_id].append(turn)
            self._store[session_id] = self._store[session_id][-self._max_items :]

    def _get_turns(self, session_id: str) -> list[dict]:
        if self._redis:
            key = f"rag:conv:{session_id}"
            raw = self._redis.lrange(key, 0, -1)
            turns = []
            for r in raw:
                try:
                    turns.append(json.loads(r))
                except Exception:
                    pass
            return turns
        return list(self._store.get(session_id, []))

    def get_history_text(self, session_id: str) -> str:
        turns = self._get_turns(session_id)
        if not turns:
            return ""
        lines = []
        for t in turns:
            label = "User" if t["role"] == "user" else "Assistant"
            lines.append(f"{label}: {t['content']}")
        return "\n".join(lines)

    def get_previous_query(self, session_id: str) -> Optional[str]:
        """Return the second-to-last user message for query expansion."""
        turns = self._get_turns(session_id)
        user_turns = [t for t in turns if t["role"] == "user"]
        if len(user_turns) >= 2:
            return user_turns[-2]["content"]
        return None


_memory: ConversationMemory | None = None


def get_memory() -> ConversationMemory:
    global _memory
    if _memory is None:
        _memory = ConversationMemory()
    return _memory
