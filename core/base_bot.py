"""
Base Bot Engine Interface for APPS_BOT.
Defines standard lifecycle methods, health checks, and status reporting.

Security Policy Source: SOUL.md §4 (Security & Governance Boundaries)
  - Zero-Crash Policy: All tool execution handlers wrapped in try/except;
    errors returned as tool results without breaking the execution loop.
  - HITL Gate: Irreversible production mutations require explicit approval.
"""

import functools
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable
from core.logger import setup_logger


def zero_crash(func: Callable) -> Callable:
    """
    Decorator implementing SOUL.md §4 Zero-Crash Policy:
    'Wrap all tool execution handlers in try/except blocks;
     return errors as tool results without breaking the execution loop.'
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger = setup_logger("ZERO_CRASH")
            logger.error(
                f"[ZERO-CRASH GUARD] Exception in '{func.__name__}': {e}. "
                f"Returning error result per SOUL.md §4 policy."
            )
            return {"error": str(e), "source": func.__name__, "policy": "SOUL.md §4 Zero-Crash"}

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger = setup_logger("ZERO_CRASH")
            logger.error(
                f"[ZERO-CRASH GUARD] Exception in '{func.__name__}': {e}. "
                f"Returning error result per SOUL.md §4 policy."
            )
            return {"error": str(e), "source": func.__name__, "policy": "SOUL.md §4 Zero-Crash"}

    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


class BaseBotEngine(ABC):
    """
    Abstract Base Class for all Bot instances in the APPS_BOT ecosystem.
    
    Governance (SOUL.md §4):
      - Zero-Crash Policy enforced via @zero_crash decorator
      - HITL Gate for irreversible mutations
      - All credentials managed via .env (Zero Plain-Text)
    """

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
