"""
QC Unit Tests for APPS_BOT Core Framework.
Verifies path localization, configuration loading, logger initialization, and AI helper fallback.
"""

import os
import sys
import unittest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.config import settings, ROOT_DIR
from core.logger import setup_logger, Colors
from core.base_bot import BaseBotEngine
from core.ai_helper import ai_helper


class DummyBot(BaseBotEngine):
    """Dummy bot implementation for lifecycle contract testing."""
    async def start(self) -> None:
        self._is_running = True

    async def stop(self) -> None:
        self._is_running = False

    def health_check(self) -> dict:
        return {"status": "ok", "mock": True}


class TestCoreFramework(unittest.TestCase):
    """QC Test Suite for Core Layer."""

    def test_path_localization(self):
        """Verify that ROOT_DIR is accurately resolved and exists."""
        self.assertTrue(os.path.exists(ROOT_DIR), f"ROOT_DIR {ROOT_DIR} should exist.")
        self.assertTrue(os.path.isabs(ROOT_DIR), "ROOT_DIR must be an absolute path.")
        self.assertTrue(os.path.exists(settings.LOGS_DIR), "LOGS_DIR should be created.")

    def test_logger_setup(self):
        """Verify that logger outputs and writes to log file."""
        test_logger = setup_logger("TEST_CORE")
        self.assertIsNotNone(test_logger)
        test_logger.info("QC Test log message execution.")
        
        log_file = os.path.join(settings.LOGS_DIR, "apps_bot.log")
        self.assertTrue(os.path.exists(log_file), "apps_bot.log must exist after logging.")

    def test_base_bot_contract(self):
        """Verify standard lifecycle contract implementation."""
        bot = DummyBot("TEST_DUMMY_BOT")
        self.assertEqual(bot.bot_name, "TEST_DUMMY_BOT")
        self.assertFalse(bot.is_running)
        
        status = bot.get_status()
        self.assertIn("bot_name", status)
        self.assertIn("health", status)
        self.assertTrue(status["health"]["mock"])

    def test_ai_helper_fallback(self):
        """Verify that AI helper summarizes text properly even offline."""
        sample_text = (
            "Pemberitahuan penting mengenai rilis sistem bot terbaru versi 1.0.0. "
            "Sistem ini mencakup modul Telegram Gmail Bot dan WhatsApp Bot. "
            "Semua modul telah melalui uji Quality Control dan dinyatakan siap operasi."
        )
        summary = ai_helper.summarize_text(sample_text, max_words=20)
        self.assertIsInstance(summary, str)
        self.assertTrue(len(summary) > 0)
        
        draft = ai_helper.draft_reply("Konfirmasi Jadwal", "Kapan sistem bot ini mulai aktif?")
        self.assertIsInstance(draft, str)
        self.assertGreater(len(draft), 20, "Draft reply should produce meaningful response.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
