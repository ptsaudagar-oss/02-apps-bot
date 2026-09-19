"""
Telegram WhatsApp Bridge Listener and Outbound Reply Engine.
Handles:
1. Callback queries from '✍️ Balas Langsung di Tele'
2. Direct text messages written inside Telegram Forum Topics -> Outbound WhatsApp message dispatch!
"""

import asyncio
import httpx
from typing import Optional, Dict, Any
from core.config import settings
from core.logger import setup_logger

try:
    from .session_manager import session_manager
except ImportError:
    from session_manager import session_manager

logger = setup_logger("TG_WA_BRIDGE")

class TelegramWABridgeListener:
    """Listens for Admin replies in Telegram and forwards them to WhatsApp."""

    def __init__(self, whatsapp_handler=None):
        self.bot_token = settings.TELEGRAM_WA_FORWARD_BOT_TOKEN
        self.forum_group_id = str(settings.TELEGRAM_WA_FORUM_GROUP_ID or "-1004466206539")
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.whatsapp_handler = whatsapp_handler
        self.client = httpx.AsyncClient(timeout=25.0)
        self._is_running = False
        self._last_update_id = 0

    async def start(self) -> None:
        """Starts long-polling for WhatsApp Telegram Forwarder Bot."""
        if not self.bot_token:
            logger.warning("TELEGRAM_WA_FORWARD_BOT_TOKEN is not configured. Bridge listener standby.")
            return

        self._is_running = True
        logger.info(f"Telegram WA Bridge Listener active on group {self.forum_group_id} (@Ada_WA_Masoex_bot)")
        
        while self._is_running:
            try:
                updates = await self._get_updates(offset=self._last_update_id + 1, timeout=10)
                for update in updates:
                    self._last_update_id = update["update_id"]
                    await self._process_update(update)
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Telegram WA Bridge polling: {e}")
                await asyncio.sleep(3)

    def stop(self) -> None:
        self._is_running = False

    async def _get_updates(self, offset: Optional[int] = None, timeout: int = 10) -> list:
        params = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset
        try:
            resp = await self.client.get(f"{self.api_url}/getUpdates", params=params, timeout=timeout + 5)
            if resp.status_code == 200:
                return resp.json().get("result", [])
        except Exception as e:
            logger.debug(f"getUpdates error: {e}")
        return []

    async def _process_update(self, update: Dict[str, Any]) -> None:
        # 1. Handle Callback Query (Click on '✍️ Balas Langsung di Tele')
        if "callback_query" in update:
            cb = update["callback_query"]
            cb_id = cb["id"]
            data = cb.get("data", "")
            cb.get("from", {}).get("first_name", "Akang")
            message = cb.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            thread_id = message.get("message_thread_id")

            if data.startswith("reply_tele:"):
                target_phone = data.split("reply_tele:")[1]
                # Acknowledge callback query immediately
                await self._answer_callback(cb_id, text=f"Mode Balas Aktif untuk +{target_phone}")

                # Send prompt message to the topic
                prompt_text = (
                    f"✍️ <b>Mode Balas Langsung Aktif</b>\n"
                    f"Silakan ketik pesan balasan Anda langsung di room topik ini, "
                    f"pesan akan otomatis terkirim ke WhatsApp <code>+{target_phone}</code>."
                )
                payload = {
                    "chat_id": chat_id,
                    "text": prompt_text,
                    "parse_mode": "HTML"
                }
                if thread_id:
                    payload["message_thread_id"] = thread_id
                await self.client.post(f"{self.api_url}/sendMessage", json=payload)
                return

            elif data.startswith("read_tele:"):
                target_phone = data.split("read_tele:")[1]
                # Tandai sudah dibaca di database lokal (Anti-Banned Safe)
                session_manager.mark_inbox_read(target_phone)
                await self._answer_callback(cb_id, text=f"Ditandai Selesai Dibaca (Anti-Banned Safe) ✅")
                
                confirm_text = f"👁️ <i>Chat dari +{target_phone} telah ditandai SELESAI DIBACA di sistem Telegram. Status WhatsApp tetap aman & privat.</i>"
                read_payload = {
                    "chat_id": chat_id,
                    "text": confirm_text,
                    "parse_mode": "HTML"
                }
                if thread_id:
                    read_payload["message_thread_id"] = thread_id
                await self.client.post(f"{self.api_url}/sendMessage", json=read_payload)
                return

        # 2. Handle Text Message inside Topic or Direct Chat
        elif "message" in update and "text" in update["message"]:
            msg = update["message"]
            chat_id = str(msg["chat"]["id"])
            thread_id = msg.get("message_thread_id")
            text = msg["text"].strip()
            sender_user = msg.get("from", {})

            # Jangan proses pesan dari bot itu sendiri
            if sender_user.get("is_bot"):
                return

            # Perintah /inbox atau /unread untuk cek daftar chat pelanggan yang belum dibalas
            if text in ("/inbox", "/unread", "/list"):
                unreads = session_manager.get_unread_inbox()
                if not unreads:
                    inbox_summary = "✅ <b>Semua pesan WhatsApp telah dibaca/direspon!</b>\nTidak ada antrean pending saat ini."
                else:
                    lines = [f"📬 <b>DAFTAR PESAN WHATSAPP BELUM DIBALAS ({len(unreads)}):</b>\n"]
                    for idx, item in enumerate(unreads, 1):
                        lines.append(
                            f"{idx}. <b>+{item['phone']}</b> ({item.get('name', 'User')})\n"
                            f"   💬 <i>\"{item.get('last_message', '')[:60]}\"</i>\n"
                            f"   ⏰ <code>{item.get('updated_at', '')}</code>"
                        )
                    inbox_summary = "\n\n".join(lines)

                reply_inbox = {
                    "chat_id": chat_id,
                    "text": inbox_summary,
                    "parse_mode": "HTML"
                }
                if thread_id:
                    reply_inbox["message_thread_id"] = thread_id
                await self.client.post(f"{self.api_url}/sendMessage", json=reply_inbox)
                return

            # Abaikan perintah lainnya
            if text.startswith("/"):
                return

            # Cek apakah pesan diketik di dalam forum topic
            target_phone = None
            if thread_id:
                target_phone = session_manager.get_phone_by_topic_id(thread_id)

            if target_phone and self.whatsapp_handler:
                logger.info(f"Admin reply received in topic {thread_id} -> Dispatching to WhatsApp +{target_phone}: '{text}'")
                
                # Kirim ke WhatsApp customer via WhatsAppMessageHandler
                success = await self.whatsapp_handler.send_message(target_phone, text)
                
                # Begitu admin balas, otomatis status unread di-resolve jadi READ
                session_manager.mark_inbox_read(target_phone)

                # Konfirmasi ke Admin di Telegram Topic
                status_icon = "✅" if success else "❌"
                status_msg = (
                    f"{status_icon} <b>Pesan Terkirim ke WhatsApp</b> <code>+{target_phone}</code>:\n"
                    f"<i>\"{text}\"</i>\n\n"
                    f"🏷️ <i>Status: RESOLVED & READ</i>"
                )
                reply_payload = {
                    "chat_id": chat_id,
                    "message_thread_id": thread_id,
                    "text": status_msg,
                    "parse_mode": "HTML",
                    "reply_to_message_id": msg["message_id"]
                }
                await self.client.post(f"{self.api_url}/sendMessage", json=reply_payload)
            elif not target_phone and thread_id:
                # Topik belum terdaftar nomornya
                logger.warning(f"No phone mapped for topic {thread_id}")

    async def _answer_callback(self, cb_id: str, text: str) -> None:
        try:
            await self.client.post(
                f"{self.api_url}/answerCallbackQuery",
                json={"callback_query_id": cb_id, "text": text}
            )
        except Exception as e:
            logger.debug(f"Failed to answer callback query: {e}")
