"""
QC Unit and Integration Tests for Telegram Gmail Bot.
Validates email fetching, command handling, AI summarization integration, and lifecycle health checks.
"""

import os
import sys
import asyncio
import unittest

# Resolve localized paths for modules with hyphens/numbers
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))

if MODULE_ROOT not in sys.path:
    sys.path.insert(0, MODULE_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.config import settings
from gmail_service import gmail_service, GmailService
from telegram_handler import telegram_handler, TelegramHandler
from main import bot_engine, TelegramGmailBotEngine


class TestGmailBotModule(unittest.TestCase):
    """QC Test Suite for Telegram Gmail Bot."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_gmail_service_simulation(self):
        """Test mock inbox fetching, detail retrieval, and mark-as-read in simulation mode."""
        svc = GmailService()
        emails = svc.get_unread_emails(limit=5)
        self.assertIsInstance(emails, list)
        self.assertGreater(len(emails), 0, "Simulation inbox should contain seed emails.")

        first_email = emails[0]
        self.assertIn("subject", first_email)
        self.assertIn("from", first_email)
        self.assertIn("body", first_email)

        # Test detail lookup
        details = svc.get_email_details(first_email["id"])
        self.assertIsNotNone(details)
        self.assertEqual(details["subject"], first_email["subject"])

        # Test mark as read
        res = svc.mark_as_read(first_email["id"])
        self.assertTrue(res)

    def test_gmail_send_simulation(self):
        """Test sending email in simulation mode."""
        svc = GmailService()
        success, msg = svc.send_email("recipient@test.com", "Testing APPS_BOT", "Content body here.")
        self.assertTrue(success)
        self.assertIn("simulated", msg.lower())

    def test_telegram_authorization(self):
        """Test chat ID whitelist logic."""
        handler = TelegramHandler(token="TEST_MOCK_TOKEN")
        # With default empty authorized list, all allowed
        self.assertTrue(handler.is_authorized("12345678"))

    def test_telegram_commands_dispatch(self):
        """Test handling commands (/start, /unread, /status, /summarize)."""
        async def run_commands():
            handler = TelegramHandler(token="")  # Simulation mode
            
            # 1. /start
            await handler.handle_command("999", "/start", "Tester")
            
            # 2. /status
            await handler.handle_command("999", "/status", "Tester")

            # 3. /unread
            await handler.handle_command("999", "/unread", "Tester")

            # 4. /summarize 101
            await handler.handle_command("999", "/summarize 101", "Tester")

            # 5. /draft 101
            await handler.handle_command("999", "/draft 101", "Tester")

            # 6. /send recipient@test.com | Title | Message
            await handler.handle_command("999", "/send test@domain.com | Subject Test | Content Test", "Tester")

        self.loop.run_until_complete(run_commands())

    def test_telegram_callbacks(self):
        """Test inline keyboard callback query actions."""
        async def run_callbacks():
            handler = TelegramHandler(token="")
            await handler.handle_callback("cb_1", "999", "summarize:101")
            await handler.handle_callback("cb_2", "999", "draft:101")
            await handler.handle_callback("cb_3", "999", "read:101")

        self.loop.run_until_complete(run_callbacks())

    def test_engine_health_check(self):
        """Test engine health check structure."""
        engine = TelegramGmailBotEngine()
        health = engine.health_check()
        self.assertIn("telegram_token_present", health)
        self.assertIn("gmail_connected", health)
        self.assertIn("engine_running", health)


if __name__ == "__main__":
    unittest.main(verbosity=2)
