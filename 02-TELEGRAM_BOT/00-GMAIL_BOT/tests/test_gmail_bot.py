"""
QC Unit and Integration Tests for Telegram Gmail Bot.
Validates email fetching, command handling, AI summarization integration, and lifecycle health checks.
"""

import os
import sys
import json
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
from gmail_service import GmailService, gmail_service
from telegram_handler import TelegramHandler, telegram_handler
from main import TelegramGmailBotEngine


class TestGmailBotModule(unittest.TestCase):
    """QC Test Suite for Telegram Gmail Bot."""

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()
        try:
            from main import STREAM_STATE_PATH
            with open(STREAM_STATE_PATH, "w", encoding="utf-8") as f:
                json.dump([], f)
        except Exception:
            pass

    def test_gmail_service_simulation(self):
        """Test mock inbox fetching, detail retrieval, and mark-as-read in simulation mode."""
        svc = GmailService()
        svc.app_password = ""  # Force simulation mode for unit isolation
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
        success, msg = svc.send_email("recipient@test.com", "Testing APPS_BOT", "Content body here.", force_simulation=True)
        self.assertTrue(success)
        self.assertIn("simulated", msg.lower())

    def test_telegram_authorization(self):
        """Test chat ID whitelist logic."""
        handler = TelegramHandler(token="TEST_MOCK_TOKEN")
        if settings.TELEGRAM_AUTHORIZED_CHAT_IDS:
            auth_id = settings.TELEGRAM_AUTHORIZED_CHAT_IDS[0]
            self.assertTrue(handler.is_authorized(auth_id))
            self.assertFalse(handler.is_authorized("unauthorized_random_chat_99999"))
        else:
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

    def test_multi_account_and_enclave_cards(self):
        """Verify dynamic buttons and tags for B2B, E-Commerce, and Privacy Enclave accounts."""
        handler = TelegramHandler(token="")

        # 1. B2B Account Card
        b2b_item = {
            "id": "201",
            "subject": "Faktur B2B Pengadaan Server",
            "from": "vendor@enterprise.com",
            "account": "pt.saudagar@gmail.com",
            "snippet": "Invoice terlampir...",
        }
        text_b2b, markup_b2b = handler._build_email_card(b2b_item)
        self.assertIn("[🏢 B2B CORPORATE]", text_b2b)
        self.assertEqual(markup_b2b["inline_keyboard"][0][0]["text"], "⚡ Ringkas AI")

        # 2. E-Commerce Store Card
        store_item = {
            "id": "202",
            "subject": "Pesanan Baru #8M-1029",
            "from": "customer@marketplace.com",
            "account": "8m.shop.online@gmail.com",
            "snippet": "Pembayaran berhasil...",
        }
        text_store, markup_store = handler._build_email_card(store_item)
        self.assertIn("[🛒 E-COMMERCE]", text_store)
        self.assertEqual(markup_store["inline_keyboard"][0][0]["text"], "🔍 Cek Detail")
        self.assertEqual(markup_store["inline_keyboard"][0][1]["text"], "⚙️ Proses Pesanan")

        # 3. Master Owner Privacy Enclave Card
        owner_item = {
            "id": "203",
            "subject": "Laporan Keuangan Rahasia",
            "from": "kafnun84@gmail.com",
            "account": "kafnun84@gmail.com",
            "snippet": "Data sensitif...",
        }
        text_owner, markup_owner = handler._build_email_card(owner_item)
        self.assertIn("[🔒 PRIVACY ENCLAVE]", text_owner)
        self.assertEqual(markup_owner["inline_keyboard"][0][0]["text"], "🛡️ HITL Otorisasi")

    def test_sliding_window_buffer(self):
        """Test that stream window enforces max 10 Primary + max 10 Update = Total 20 FIFO items."""
        from unittest.mock import patch, AsyncMock

        engine = TelegramGmailBotEngine()
        engine._stream_window = []

        # Record 12 PRIMARY items
        for i in range(1, 13):
            engine._record_stream_entry(
                email_id=f"P{i}",
                chat_id="999",
                message_id=5000 + i,
                subject=f"Primary Subject {i}",
                category="PRIMARY"
            )

        # Record 12 UPDATES items
        for i in range(1, 13):
            engine._record_stream_entry(
                email_id=f"U{i}",
                chat_id="999",
                message_id=6000 + i,
                subject=f"Update Subject {i}",
                category="UPDATES"
            )

        self.assertEqual(len(engine._stream_window), 24)

        with patch.object(telegram_handler, "delete_message", new_callable=AsyncMock) as mock_del, \
             patch.object(gmail_service, "mark_as_read", return_value=True) as mock_read:
            # Enforce sliding window (should evict 2 oldest PRIMARY and 2 oldest UPDATES)
            self.loop.run_until_complete(engine._enforce_stream_window())
            self.assertEqual(mock_del.call_count, 4)
            self.assertEqual(mock_read.call_count, 4)

        self.assertEqual(len(engine._stream_window), 20)
        primary_entries = [e for e in engine._stream_window if e["category"] == "PRIMARY"]
        update_entries = [e for e in engine._stream_window if e["category"] == "UPDATES"]

        self.assertEqual(len(primary_entries), 10)
        self.assertEqual(len(update_entries), 10)

        # Oldest remaining PRIMARY should be P3, newest P12
        self.assertEqual(primary_entries[0]["email_id"], "P3")
        self.assertEqual(primary_entries[-1]["email_id"], "P12")

        # Oldest remaining UPDATE should be U3, newest U12
        self.assertEqual(update_entries[0]["email_id"], "U3")
        self.assertEqual(update_entries[-1]["email_id"], "U12")

    def test_category_filtering(self):
        """Verify that get_unread_emails_by_category only returns PRIMARY and UPDATES."""
        svc = GmailService()
        svc.app_password = ""  # Simulation
        svc._mock_data = [
            {"id": "1", "subject": "P1", "from": "a@b.com", "body": "x", "is_read": False, "category": "PRIMARY"},
            {"id": "2", "subject": "U1", "from": "a@b.com", "body": "x", "is_read": False, "category": "UPDATES"},
            {"id": "3", "subject": "Promo", "from": "a@b.com", "body": "x", "is_read": False, "category": "PROMOTIONS"},
            {"id": "4", "subject": "Social", "from": "a@b.com", "body": "x", "is_read": False, "category": "SOCIAL"},
        ]
        emails = svc.get_unread_emails_by_category(categories=["primary", "updates"], limit_per_category=10)
        self.assertEqual(len(emails), 2)
        categories = [e["category"].upper() for e in emails]
        self.assertIn("PRIMARY", categories)
        self.assertIn("UPDATES", categories)
        self.assertNotIn("PROMOTIONS", categories)
        self.assertNotIn("SOCIAL", categories)

    def test_gmail_clean_backlog(self):
        """Test clean_inbox_backlog simulation."""
        svc = GmailService()
        svc.app_password = ""  # Simulation
        svc._mock_data = [{"id": str(i), "is_read": False} for i in range(15)]
        cleaned = svc.clean_inbox_backlog(keep_latest=10)
        self.assertEqual(cleaned, 5)
        self.assertEqual(len(svc._mock_data), 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
