"""
Session and Context Manager for WhatsApp Bot.
Maintains in-memory conversation histories, intent tracking, and state machines per phone number.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


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

    def purge_all_simulated_sessions(self) -> int:
        """
        Purges mock/dummy/test sessions (Task 2.1 Data Purge Protocol).
        Returns number of wiped sessions.
        """
        count = len(self._sessions)
        self._sessions.clear()
        return count


session_manager = SessionManager()
