"""
Message Dispatcher and Payload Parser for WhatsApp Bot.
Processes Meta WhatsApp Cloud API webhooks, handles conversational routing, and sends responses.

Context Injection Sources:
  - SOUL.md §1: Bot Identity → greeting menu
  - MEMORY.md §1: Architecture → status command
  - USER.md §2: Communication Style → AI response tone
"""

import httpx
from typing import Dict, Any, List, Tuple
from core.config import settings
from core.logger import setup_logger
from core.ai_helper import ai_helper
from core import context_loader
from core.privacy_enclave import privacy_enclave
from core.telemetry import telemetry_hub
import time
import asyncio

try:
    from .session_manager import session_manager, UserSession
    from .config import (
        WHATSAPP_ACCESS_TOKEN,
        WHATSAPP_PHONE_NUMBER_ID,
        WHATSAPP_API_VERSION,
        WHATSAPP_GATEWAY_URL,
        WHATSAPP_PROVIDER_PRIMARY,
        WHATSAPP_LOCAL_GATEWAY_URL,
        WHATSAPP_FAILOVER_TO_LOCAL
    )
except ImportError:
    from session_manager import session_manager
    from config import (
        WHATSAPP_ACCESS_TOKEN,
        WHATSAPP_PHONE_NUMBER_ID,
        WHATSAPP_API_VERSION,
        WHATSAPP_GATEWAY_URL,
        WHATSAPP_PROVIDER_PRIMARY,
        WHATSAPP_LOCAL_GATEWAY_URL,
        WHATSAPP_FAILOVER_TO_LOCAL
    )

logger = setup_logger("WA_HANDLER")


class WhatsAppMessageHandler:
    """Handles incoming WhatsApp events and outbound message dispatch."""

    def __init__(self):
        self.access_token = WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = WHATSAPP_PHONE_NUMBER_ID
        self.api_url = f"{WHATSAPP_GATEWAY_URL}/{WHATSAPP_API_VERSION}/{self.phone_number_id}/messages"
        self.primary_provider = WHATSAPP_PROVIDER_PRIMARY
        self.local_gateway_url = WHATSAPP_LOCAL_GATEWAY_URL
        self.failover_to_local = WHATSAPP_FAILOVER_TO_LOCAL
        self.client = httpx.AsyncClient(timeout=25.0)
        # Pre-load bot identity from SOUL.md + USER.md
        self._identity = context_loader.get_bot_identity()

    def is_configured(self) -> bool:
        """Checks if either Meta or Local Gateway is configured."""
        return bool((self.access_token and self.phone_number_id) or self.local_gateway_url)

    def is_meta_configured(self) -> bool:
        """Checks if Meta WhatsApp Cloud API credentials are validly supplied."""
        return bool(self.access_token and self.phone_number_id)

    def parse_incoming_webhook(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parses Meta WhatsApp Webhook payload and extracts clean message objects.
        Supports both standard Meta Cloud API and simplified webhook bridge formats.
        """
        parsed_messages: List[Dict[str, Any]] = []

        # 1. Meta Cloud API Standard Format
        if payload.get("object") == "whatsapp_business_account":
            entries = payload.get("entry", [])
            for entry in entries:
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    contacts = {c["wa_id"]: c.get("profile", {}).get("name", "User") for c in value.get("contacts", [])}
                    messages = value.get("messages", [])

                    for msg in messages:
                        sender = msg.get("from")
                        msg_id = msg.get("id")
                        msg_type = msg.get("type", "text")
                        timestamp = msg.get("timestamp")

                        body = ""
                        if msg_type == "text":
                            body = msg.get("text", {}).get("body", "")
                        elif msg_type == "button":
                            body = msg.get("button", {}).get("text", "")
                        elif msg_type == "interactive":
                            interactive = msg.get("interactive", {})
                            if interactive.get("type") == "button_reply":
                                body = interactive.get("button_reply", {}).get("title", "")
                            elif interactive.get("type") == "list_reply":
                                body = interactive.get("list_reply", {}).get("title", "")

                        parsed_messages.append({
                            "sender": sender,
                            "sender_name": contacts.get(sender, "User"),
                            "message_id": msg_id,
                            "type": msg_type,
                            "body": body.strip(),
                            "timestamp": timestamp
                        })

        # 2. Simplified Bridge / Custom Gateway Format
        elif "sender" in payload and "body" in payload:
            parsed_messages.append({
                "sender": str(payload.get("sender")),
                "sender_name": str(payload.get("sender_name", "User")),
                "message_id": str(payload.get("id", "msg_mock")),
                "type": str(payload.get("type", "text")),
                "body": str(payload.get("body", "")).strip(),
                "timestamp": str(payload.get("timestamp", ""))
            })

        return parsed_messages

    async def process_message(self, message: Dict[str, Any]) -> str:
        """
        Evaluates incoming user message, routes intent, and returns response string.
        Also tracks context in session_manager.
        """
        sender = message["sender"]
        sender_name = message.get("sender_name", "User")
        body = message["body"]

        session = session_manager.get_or_create_session(sender)

        # Apply Privacy Enclave PII Redaction on incoming text
        sanitized_body = privacy_enclave.redact_pii(body) if settings.ENCLAVE_PII_REDACTION else body
        session.add_message("user", sanitized_body)
        clean_text = sanitized_body.lower().strip()

        logger.info(f"Incoming WhatsApp message from {sender} ({sender_name}): '{body}'")

        # ⚡ REAL-TIME DISPATCH: Teruskan chat WA masuk ke Telegram Master Owner (Satu Pintu Komando)
        try:
            if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_AUTHORIZED_CHAT_IDS:
                wa_forward_text = (
                    f"🟢 <b>[WHATSAPP CHAT MASUK]</b> 💬\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"• <b>Dari:</b> <code>+{sender}</code> ({sender_name})\n"
                    f"• <b>Pesan:</b> {body}\n"
                    f"• <b>Waktu:</b> <code>{time.strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"⚡ <i>Dual-Channel WhatsApp-to-Telegram Bridge</i>"
                )
                for chat_id in settings.TELEGRAM_AUTHORIZED_CHAT_IDS:
                    asyncio.create_task(
                        self.client.post(
                            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                            json={
                                "chat_id": chat_id,
                                "text": wa_forward_text,
                                "parse_mode": "HTML"
                            },
                            timeout=5.0
                        )
                    )
        except Exception as forward_err:
            logger.error(f"Error dispatching WA message to Telegram: {forward_err}")

        # Command & Keyword Routing
        if any(w in clean_text for w in ("halo", "hai", "hi", "menu", "start", "help")):
            reply = (
                f"👋 *Halo, {sender_name}!*\n"
                f"Selamat datang di layanan *{self._identity['name']}* 🤖📱\n"
                f"_{self._identity['role']}_\n"
                f"_Powered by {self._identity['organization']}_\n\n"
                f"📌 *Pilihan Layanan Cepat:*\n"
                f"1️⃣ *Info Sistem* - Ketik *status*\n"
                f"2️⃣ *Email Terpadu* - Ketik *email*\n"
                f"3️⃣ *Konsultasi AI* - Ketik pertanyaan apa saja secara langsung\n"
                f"4️⃣ *Reset Sesi* - Ketik *reset*\n\n"
                f"Ada yang dapat kami bantu hari ini?"
            )

        elif clean_text == "status":
            reply = (
                f"📊 *Status Layanan {self._identity['name']}*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"• *Identitas:* {self._identity['name']}\n"
                f"• *Organisasi:* {self._identity['organization']}\n"
                f"• *Metodologi:* {self._identity['methodology']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"• *Server Status:* ONLINE ✅\n"
                f"• *Kredensial API:* {'META CLOUD API' if self.is_configured() else 'SIMULASI LOKAL'}\n"
                f"• *User Session ID:* {session.phone_number}\n"
                f"• *Interaksi Aktif:* {len(session.history)} pesan\n"
                f"• *AI Assistant Engine:* {'Gemini 3.6 Flash' if settings.GEMINI_API_KEY else 'Heuristic Engine'}"
            )

        elif any(w in clean_text for w in ("email", "cek email", "inbox", "gmail")):
            reply = (
                f"📬 *Integrasi Gmail APPS_BOT*\n"
                f"Sistem bot email terhubung dengan modul *02-TELEGRAM_BOT/00-GMAIL_BOT*.\n\n"
                f"Ketik */unread* di bot Telegram Anda atau akses menu terpusat via `apps_bot_manager.py`."
            )

        elif clean_text in ("reset", "clear"):
            session.reset()
            reply = "🔄 Sesi percakapan Anda telah berhasil direset. Silakan ketik *menu* untuk memulai kembali."

        else:
            # AI Assistant Fallback
            logger.info(f"Routing to AI Assistant for inquiry: '{body}'")
            reply = ai_helper.draft_reply(
                subject=f"Inquiry WhatsApp dari {sender_name}",
                body=body,
                tone="ramah, profesional, dan solutif"
            )

        session.add_message("assistant", reply)
        # Dispatch message to user
        await self.send_message(sender, reply)
        return reply

    async def _send_via_meta(self, clean_phone: str, text: str) -> Tuple[bool, str]:
        """Dispatches message through Meta WhatsApp Cloud API."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": clean_phone,
            "type": "text",
            "text": {"body": text}
        }
        try:
            resp = await self.client.post(self.api_url, headers=headers, json=payload)
            if resp.status_code in (200, 201):
                logger.info(f"[META CLOUD API] Message successfully dispatched to +{clean_phone}")
                return True, "SUCCESS_META"
            else:
                logger.warning(f"[META CLOUD API FAILED] Status {resp.status_code}: {resp.text}")
                return False, f"HTTP_{resp.status_code}_{resp.text}"
        except Exception as e:
            logger.warning(f"[META CLOUD API ERROR] Connection failure: {e}")
            return False, str(e)

    async def _send_via_local_gateway(self, clean_phone: str, text: str) -> Tuple[bool, str]:
        """Dispatches message through Local Gateway Bridge (Baileys/WPPConnect/Custom Bridge)."""
        payload = {
            "to": clean_phone,
            "phone": clean_phone,
            "message": text,
            "text": text
        }
        try:
            resp = await self.client.post(self.local_gateway_url, json=payload, timeout=10.0)
            if resp.status_code in (200, 201):
                logger.info(f"[LOCAL GATEWAY] Message successfully dispatched to +{clean_phone}")
                return True, "SUCCESS_LOCAL_GATEWAY"
            else:
                logger.warning(f"[LOCAL GATEWAY FAILED] Status {resp.status_code}: {resp.text}")
                return False, f"HTTP_{resp.status_code}"
        except Exception as e:
            logger.debug(f"[LOCAL GATEWAY OFFLINE] {e}. Falling back to simulation mode.")
            return False, str(e)

    async def send_message(self, recipient_phone: str, text: str) -> bool:
        """
        Sends an outbound WhatsApp text message.
        Strategy per QC & User Request: 'Meta dahulu. Jika gagal, ke lokal gateway saja'
        """
        clean_phone = str(recipient_phone).replace("+", "").replace("-", "").strip()

        # 1. Prioritas Utama: Meta WhatsApp Cloud API
        if self.is_meta_configured():
            success, info = await self._send_via_meta(clean_phone, text)
            if success:
                telemetry_hub.record_dispatch("meta", is_failover=False)
                return True

            if self.failover_to_local:
                logger.warning(
                    f"⚠️ [FAILOVER TRIGGERED] Meta API gagal ({info}). "
                    f"Mengalihkan pengiriman ke Local Gateway: {self.local_gateway_url}..."
                )
            else:
                logger.error(f"Meta API gagal dan failover lokal dinonaktifkan: {info}")
                return False
        else:
            logger.debug("Meta Cloud API belum dikonfigurasi. Mengalihkan langsung ke Local Gateway...")

        # 2. Jalur Failover: Local Gateway Bridge
        if self.failover_to_local and self.local_gateway_url:
            success_local, info_local = await self._send_via_local_gateway(clean_phone, text)
            if success_local:
                telemetry_hub.record_dispatch("local_bridge", is_failover=True)
                return True

        # 3. Fail-safe Simulation / Mock Mode jika kedua jalur belum aktif / offline
        telemetry_hub.record_dispatch("simulation", is_failover=False)
        logger.info(f"[SIMULASI WHATSAPP - FALLBACK AMAN] Ke: +{clean_phone} ->\n{text}")
        return True


whatsapp_handler = WhatsAppMessageHandler()
