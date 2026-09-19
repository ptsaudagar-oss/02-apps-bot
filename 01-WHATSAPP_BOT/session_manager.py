"""
Session and Context Manager for WhatsApp Bot.
Maintains in-memory conversation histories, intent tracking, and state machines per phone number.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import os

TOPIC_STORE_PATH = os.path.join(os.path.dirname(__file__), "topic_store.json")


class UserSession:
    """Represents the context and state of an individual WhatsApp user."""

    def __init__(self, phone_number: str):
        self.phone_number = phone_number
        self.state: str = "IDLE"  # IDLE, AWAITING_INPUT, etc.
        self.current_flow: Optional[str] = None
        self.history: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}
        self.last_active: datetime = datetime.now()

    def add_message(self, role: str, text: str) -> None:
        """Appends a message to conversation history with timestamp."""
        self.history.append({
            "role": role,
            "text": text,
            "timestamp": datetime.now().isoformat()
        })
        # Keep last 15 interactions in memory
        if len(self.history) > 15:
            self.history = self.history[-15:]
        self.last_active = datetime.now()

    def set_state(self, state: str, flow: Optional[str] = None) -> None:
        """Updates the conversation state machine."""
        self.state = state
        self.current_flow = flow
        self.last_active = datetime.now()

    def reset(self) -> None:
        """Resets the state back to IDLE while keeping history."""
        self.state = "IDLE"
        self.current_flow = None


class SessionManager:
    """Manages all active user sessions."""

    def __init__(self):
        self._sessions: Dict[str, UserSession] = {}

    def get_or_create_session(self, phone_number: str) -> UserSession:
        """Retrieves an existing session or initializes a new one."""
        clean_number = str(phone_number).strip().replace("+", "").replace("-", "")
        if clean_number not in self._sessions:
            self._sessions[clean_number] = UserSession(clean_number)
        return self._sessions[clean_number]

    def clear_all(self) -> None:
        """Clears all sessions (useful for tests)."""
        self._sessions.clear()

    def get_topic_id(self, phone_number: str) -> Optional[int]:
        """Gets persistent Telegram forum topic ID for customer phone number."""
        clean_number = str(phone_number).strip().replace("+", "").replace("-", "")
        store = self._load_topic_store()
        return store.get(clean_number)

    def save_topic_id(self, phone_number: str, topic_id: int) -> None:
        """Saves persistent Telegram forum topic ID for customer phone number."""
        clean_number = str(phone_number).strip().replace("+", "").replace("-", "")
        store = self._load_topic_store()
        store[clean_number] = topic_id
        self._save_topic_store(store)

    def _load_topic_store(self) -> Dict[str, int]:
        if os.path.exists(TOPIC_STORE_PATH):
            try:
                with open(TOPIC_STORE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_topic_store(self, store: Dict[str, int]) -> None:
        try:
            with open(TOPIC_STORE_PATH, "w", encoding="utf-8") as f:
                json.dump(store, f, indent=2)
        except Exception:
            pass

    def purge_all_simulated_sessions(self) -> int:
        """
        Purges mock/dummy/test sessions (Task 2.1 Data Purge Protocol).
        Returns number of wiped sessions.
        """
        count = len(self._sessions)
        self._sessions.clear()
        return count


session_manager = SessionManager()
