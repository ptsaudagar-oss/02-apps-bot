"""
Base Bot Engine Interface for APPS_BOT.
Defines standard lifecycle methods, health checks, and status reporting.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from core.logger import setup_logger


class BaseBotEngine(ABC):
    """Abstract Base Class for all Bot instances in the APPS_BOT ecosystem."""

    def __init__(self, bot_name: str):
        self.bot_name = bot_name
        self.logger = setup_logger(bot_name)
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """Returns True if the bot engine is actively running."""
        return self._is_running

    @abstractmethod
    async def start(self) -> None:
        """Asynchronously starts the bot engine and listeners."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Gracefully stops the bot engine."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Performs a sanity check on dependencies, tokens, and connections."""
        pass

    def get_status(self) -> Dict[str, Any]:
        """Returns standard runtime status metadata."""
        return {
            "bot_name": self.bot_name,
            "is_running": self._is_running,
            "health": self.health_check()
        }
