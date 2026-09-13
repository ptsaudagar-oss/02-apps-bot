"""
Message Dispatcher and Payload Parser for WhatsApp Bot.
Processes Meta WhatsApp Cloud API webhooks, handles conversational routing, and sends responses.
"""

import httpx
from typing import Dict, Any, Optional, List, Tuple
from core.config import settings
from core.logger import setup_logger
from core.ai_helper import ai_helper

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
    from session_manager import session_manager, UserSession
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
        clean_text = body.lower().strip()

        session = session_manager.get_or_create_session(sender)
        session.add_message("user", body)

        logger.info(f"Incoming WhatsApp message from {sender} ({sender_name}): '{body}'")

        # Command & Keyword Routing
        if any(w in clean_text for w in ("halo", "hai", "hi", "menu", "start", "help")):
            reply = (
                f"👋 *Halo, {sender_name}!*\n"
                f"Selamat datang di layanan *APPS_BOT WhatsApp Assistant* 🤖📱\n\n"
                f"📌 *Pilihan Layanan Cepat:*\n"
                f"1️⃣ *Info Sistem* - Ketik *status*\n"
                f"2️⃣ *Email Terpadu* - Ketik *email*\n"
                f"3️⃣ *Konsultasi AI* - Ketik pertanyaan apa saja secara langsung\n"
                f"4️⃣ *Reset Sesi* - Ketik *reset*\n\n"
                f"Ada yang dapat kami bantu hari ini?"
            )

        elif clean_text == "status":
            reply = (
                f"📊 *Status Layanan WhatsApp Bot*\n"
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
                f"Sistem bot email terhubung dengan modul *00-TELEGRAM_BOT/00-G-MAIL_BOT*.\n\n"
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
                return True

        # 3. Fail-safe Simulation / Mock Mode jika kedua jalur belum aktif / offline
        logger.info(f"[SIMULASI WHATSAPP - FALLBACK AMAN] Ke: +{clean_phone} ->\n{text}")
        return True


whatsapp_handler = WhatsAppMessageHandler()
