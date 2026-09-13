"""
QC Unit and Integration Tests for WhatsApp Bot Module.
Tests FastAPI webhook endpoints, verification challenge, payload parsing, session tracking, and direct API dispatch.
"""

import os
import sys
import unittest
import asyncio
from starlette.testclient import TestClient

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULE_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))

if MODULE_ROOT not in sys.path:
    sys.path.insert(0, MODULE_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from main import app, bot_engine
from config import WHATSAPP_VERIFY_TOKEN
from session_manager import session_manager
from message_handler import whatsapp_handler


class TestWhatsAppBotModule(unittest.TestCase):
    """QC Test Suite for WhatsApp Bot Module."""

    def setUp(self):
        self.client = TestClient(app)
        session_manager.clear_all()

    def test_health_root_endpoint(self):
        """Test GET / returns 200 OK and service metadata."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "online")
        self.assertTrue(data["verify_token_active"])

    def test_webhook_verification_success(self):
        """Test Meta webhook verification handshake with correct token."""
        challenge = "random_challenge_xyz_9988"
        params = {
            "hub.mode": "subscribe",
            "hub.verify_token": WHATSAPP_VERIFY_TOKEN,
            "hub.challenge": challenge
        }
        resp = self.client.get("/webhook", params=params)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.text, challenge)

    def test_webhook_verification_invalid_token(self):
        """Test Meta webhook verification fails with 403 on invalid token."""
        params = {
            "hub.mode": "subscribe",
            "hub.verify_token": "INVALID_WRONG_TOKEN",
            "hub.challenge": "12345"
        }
        resp = self.client.get("/webhook", params=params)
        self.assertEqual(resp.status_code, 403)

    def test_webhook_incoming_message_meta_format(self):
        """Test webhook processing with realistic Meta Cloud API payload."""
        sample_meta_payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "ACCOUNT_ID_100",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "628123456789",
                                    "phone_number_id": "100200300"
                                },
                                "contacts": [
                                    {
                                        "profile": {"name": "Ahmad User"},
                                        "wa_id": "628111222333"
                                    }
                                ],
                                "messages": [
                                    {
                                        "from": "628111222333",
                                        "id": "wamid.HBgL...",
                                        "timestamp": "1726230000",
                                        "text": {"body": "Halo, saya ingin tanya status bot"},
                                        "type": "text"
                                    }
                                ]
                            },
                            "field": "messages"
                        }
                    ]
                }
            ]
        }

        resp = self.client.post("/webhook", json=sample_meta_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "EVENT_RECEIVED")
        self.assertEqual(data["processed_count"], 1)

    def test_session_manager_and_message_processing(self):
        """Test that user session records conversation history properly."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def run_process():
            msg = {
                "sender": "628199988877",
                "sender_name": "Budi Santoso",
                "body": "halo",
                "type": "text"
            }
            reply = await whatsapp_handler.process_message(msg)
            self.assertIn("Halo, Budi Santoso", reply)

            # Test status command
            msg["body"] = "status"
            reply_status = await whatsapp_handler.process_message(msg)
            self.assertIn("Status Layanan WhatsApp Bot", reply_status)

            # Verify session history
            session = session_manager.get_or_create_session("628199988877")
            self.assertGreaterEqual(len(session.history), 4)

        loop.run_until_complete(run_process())
        loop.close()

    def test_direct_api_send_endpoint(self):
        """Test POST /api/send sends outbound message in simulation mode."""
        payload = {
            "to": "628123456789",
            "message": "Pemberitahuan: Sistem bot berhasil dikonfigurasi!"
        }
        resp = self.client.post("/api/send", json=payload)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "success")

    def test_meta_to_local_failover_policy(self):
        """Test 'Meta dahulu, jika gagal ke lokal gateway' failover mechanism."""
        from unittest.mock import patch
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def run_failover():
            handler = whatsapp_handler
            # Mock Meta to fail, triggering failover to local gateway
            with patch.object(handler, "_send_via_meta", return_value=(False, "HTTP_500_META_DOWN")) as mock_meta:
                with patch.object(handler, "_send_via_local_gateway", return_value=(True, "SUCCESS")) as mock_local:
                    handler.access_token = "TEST_TOKEN"
                    handler.phone_number_id = "12345"
                    res = await handler.send_message("628123456789", "Halo Failover Test")
                    self.assertTrue(res)
                    mock_meta.assert_called_once()
                    mock_local.assert_called_once()

        loop.run_until_complete(run_failover())
        loop.close()

    def test_engine_health_check(self):
        """Test WhatsAppBotEngine health check metadata."""
        health = bot_engine.health_check()
        self.assertIn("verify_token_set", health)
        self.assertIn("port", health)
        self.assertIn("engine_running", health)


if __name__ == "__main__":
    unittest.main(verbosity=2)
