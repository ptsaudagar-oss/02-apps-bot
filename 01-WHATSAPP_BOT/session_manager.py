"""
Session and Context Manager for WhatsApp Bot.
Maintains in-memory conversation histories, intent tracking, and state machines per phone number.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import os

TOPIC_STORE_PATH = os.path.join(os.path.dirname(__file__), "topic_store.json")
INBOX_STATE_PATH = os.path.join(os.path.dirname(__file__), "inbox_state.json")


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

    def get_phone_by_topic_id(self, topic_id: int) -> Optional[str]:
        """Gets customer phone number associated with a Telegram forum topic ID."""
        store = self._load_topic_store()
        for phone, tid in store.items():
            if tid == topic_id:
                return phone
        return None

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

    # ==========================================
    # Anti-Banned Safe Inbox Unread State Manager
    # ==========================================
    def record_inbound_message(self, phone_number: str, sender_name: str, message_text: str, topic_id: Optional[int] = None) -> None:
        """Records incoming WhatsApp message as UNREAD without triggering WhatsApp read-receipts."""
        clean_number = str(phone_number).strip().replace("+", "").replace("-", "")
        state = self._load_inbox_state()
        if clean_number not in state:
            state[clean_number] = {
                "phone": clean_number,
                "name": sender_name,
                "topic_id": topic_id,
                "status": "UNREAD",
                "unread_count": 0,
                "last_message": message_text,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        state[clean_number]["name"] = sender_name
        state[clean_number]["status"] = "UNREAD"
        state[clean_number]["unread_count"] = state[clean_number].get("unread_count", 0) + 1
        state[clean_number]["last_message"] = message_text
        state[clean_number]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if topic_id:
            state[clean_number]["topic_id"] = topic_id
        self._save_inbox_state(state)

    def mark_inbox_read(self, phone_number: str) -> bool:
        """Marks a customer thread as READ internally in Telegram without alerting customer."""
        clean_number = str(phone_number).strip().replace("+", "").replace("-", "")
        state = self._load_inbox_state()
        if clean_number in state:
            state[clean_number]["status"] = "READ"
            state[clean_number]["unread_count"] = 0
            state[clean_number]["read_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._save_inbox_state(state)
            return True
        return False

    def get_unread_inbox(self) -> List[Dict[str, Any]]:
        """Returns list of all conversations currently in UNREAD status."""
        state = self._load_inbox_state()
        return [data for data in state.values() if data.get("status") == "UNREAD"]

    def _load_inbox_state(self) -> Dict[str, Any]:
        if os.path.exists(INBOX_STATE_PATH):
            try:
                with open(INBOX_STATE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_inbox_state(self, state: Dict[str, Any]) -> None:
        try:
            with open(INBOX_STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
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
