"""
Telegram Bot Handler for Gmail Assistant.
Manages interactive commands, inline keyboards, message formatting, and Telegram Bot API communication via httpx.
"""

import httpx
from typing import Dict, Any, Optional, List, Tuple
from core.config import settings
from core.logger import setup_logger
from core.ai_helper import ai_helper
try:
    from .gmail_service import gmail_service
except ImportError:
    from gmail_service import gmail_service

logger = setup_logger("TELEGRAM_HANDLER")


class TelegramHandler:
    """Async Telegram API Handler and Message Dispatcher."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.client = httpx.AsyncClient(timeout=30.0)

    def is_authorized(self, chat_id: Any) -> bool:
        """Verifies if chat_id is allowed. If whitelist is empty, allow all."""
        authorized_ids = settings.TELEGRAM_AUTHORIZED_CHAT_IDS
        if not authorized_ids:
            return True
        return str(chat_id) in authorized_ids

    async def send_message(
        self,
        chat_id: Any,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Sends a text message via Telegram API."""
        if not self.token:
            logger.info(f"[SIMULASI TELEGRAM] Chat {chat_id} -> {text[:100]}...")
            return True

        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            resp = await self.client.post(f"{self.api_url}/sendMessage", json=payload)
            if resp.status_code == 200:
                return True
            else:
                logger.error(f"Telegram API error {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    async def answer_callback_query(self, callback_query_id: str, text: Optional[str] = None) -> bool:
        """Acknowledges inline keyboard callback click."""
        if not self.token:
            return True

        payload: Dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text

        try:
            resp = await self.client.post(f"{self.api_url}/answerCallbackQuery", json=payload)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Callback answer error: {e}")
            return False

    async def get_updates(self, offset: Optional[int] = None, timeout: int = 15) -> List[Dict[str, Any]]:
        """Long-polls Telegram for new updates."""
        if not self.token:
            return []

        params: Dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset

        try:
            resp = await self.client.get(f"{self.api_url}/getUpdates", params=params, timeout=timeout + 5)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("result", [])
        except Exception as e:
            logger.debug(f"Telegram polling update error: {e}")

        return []

    async def handle_command(self, chat_id: Any, command_text: str, user_name: str = "User") -> None:
        """Dispatches commands sent by users."""
        if not self.is_authorized(chat_id):
            await self.send_message(
                chat_id,
                "⚠️ <b>Akses Ditolak</b>: Akun/Chat Anda tidak terdaftar dalam whitelist otorisasi."
            )
            return

        cmd = command_text.strip()
        cmd_parts = cmd.split(maxsplit=1)
        base_cmd = cmd_parts[0].lower()
        args = cmd_parts[1] if len(cmd_parts) > 1 else ""

        if base_cmd in ("/start", "/help"):
            msg = (
                f"👋 <b>Halo, {user_name}!</b>\n"
                f"Selamat datang di <b>APPS_BOT Gmail Assistant</b> 🤖✉️\n\n"
                f"<b>Perintah Tersedia:</b>\n"
                f"📬 <code>/unread</code> - Cek email masuk yang belum dibaca\n"
                f"📊 <code>/status</code> - Cek kesehatan koneksi bot & Gmail\n"
                f"⚡ <code>/summarize &lt;ID&gt;</code> - Minta ringkasan AI untuk email tertentu\n"
                f"📝 <code>/draft &lt;ID&gt;</code> - Buat draf balasan cerdas via AI\n"
                f"📨 <code>/send &lt;tujuan&gt; | &lt;subjek&gt; | &lt;pesan&gt;</code> - Kirim email\n\n"
                f"<i>Status Mode: {'LIVE GMAIL' if gmail_service.is_configured() else 'SIMULASI MOCK'}</i>"
            )
            await self.send_message(chat_id, msg)

        elif base_cmd in ("/unread", "/inbox"):
            emails = gmail_service.get_unread_emails(limit=5)
            if not emails:
                await self.send_message(chat_id, "🎉 <b>Kotak Masuk Bersih!</b> Tidak ada email baru yang belum dibaca.")
                return

            await self.send_message(chat_id, f"📬 <b>Ditemukan {len(emails)} Email Belum Dibaca:</b>")
            for item in emails:
                text_card, markup = self._build_email_card(item)
                await self.send_message(chat_id, text_card, reply_markup=markup)

        elif base_cmd == "/status":
            connected, msg_conn = gmail_service.check_connection()
            status_text = (
                f"⚙️ <b>Status Sistem APPS_BOT - Gmail Telegram</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• <b>Bot Engine:</b> AKTIF ✅\n"
                f"• <b>Telegram Token:</b> {'TERHUBUNG' if self.token else 'SIMULASI'} 🔑\n"
                f"• <b>Gmail Account:</b> <code>{gmail_service.email_address or 'Belum Disetel'}</code>\n"
                f"• <b>Status Gmail:</b> {'TERHUBUNG' if connected else 'OFFLINE/SIMULASI'}\n"
                f"• <b>Catatan:</b> {msg_conn}\n"
                f"• <b>Gemini AI:</b> {'AKTIF (gemini-3.6-flash)' if settings.GEMINI_API_KEY else 'OFFLINE HEURISTIC'}\n"
            )
            await self.send_message(chat_id, status_text)

        elif base_cmd == "/summarize":
            if not args:
                await self.send_message(chat_id, "⚠️ Format salah. Gunakan: <code>/summarize &lt;ID_EMAIL&gt;</code>")
                return

            email_item = gmail_service.get_email_details(args.strip())
            if not email_item:
                await self.send_message(chat_id, f"❌ Email dengan ID <code>{args}</code> tidak ditemukan.")
                return

            await self.send_message(chat_id, f"⏳ <i>Sedang menganalisis & meringkas email ID {args}...</i>")
            summary = ai_helper.summarize_text(email_item["body"])
            reply_text = (
                f"⚡ <b>Ringkasan Eksekutif AI</b>\n"
                f"<b>Subjek:</b> {email_item['subject']}\n"
                f"<b>Dari:</b> {email_item['from']}\n\n"
                f"📋 <b>Hasil Analisis:</b>\n{summary}"
            )
            await self.send_message(chat_id, reply_text)

        elif base_cmd == "/draft":
            if not args:
                await self.send_message(chat_id, "⚠️ Format salah. Gunakan: <code>/draft &lt;ID_EMAIL&gt;</code>")
                return

            email_item = gmail_service.get_email_details(args.strip())
            if not email_item:
                await self.send_message(chat_id, f"❌ Email dengan ID <code>{args}</code> tidak ditemukan.")
                return

            draft = ai_helper.draft_reply(email_item["subject"], email_item["body"])
            reply_text = (
                f"📝 <b>Draf Balasan AI</b>\n"
                f"<b>Untuk:</b> {email_item['from']}\n"
                f"<b>Re:</b> {email_item['subject']}\n\n"
                f"<code>{draft}</code>"
            )
            await self.send_message(chat_id, reply_text)

        elif base_cmd == "/send":
            parts = [p.strip() for p in args.split("|")]
            if len(parts) < 3:
                guide = (
                    "⚠️ <b>Format Pengiriman Email:</b>\n"
                    "<code>/send tujuan@email.com | Subjek Pesan | Isi Pesan Anda</code>"
                )
                await self.send_message(chat_id, guide)
                return

            to_addr, subj, body_msg = parts[0], parts[1], parts[2]
            success, msg_result = gmail_service.send_email(to_addr, subj, body_msg)
            if success:
                await self.send_message(chat_id, f"✅ <b>Berhasil Dikirim!</b>\nKe: <code>{to_addr}</code>\nSubjek: {subj}")
            else:
                await self.send_message(chat_id, f"❌ <b>Gagal Mengirim:</b> {msg_result}")

        else:
            await self.send_message(
                chat_id,
                f"❓ Perintah <code>{base_cmd}</code> tidak dikenali. Ketik <code>/help</code> untuk melihat daftar perintah."
            )

    async def handle_callback(
        self,
        callback_id: str,
        chat_id: Any,
        data: str,
        message_id: Optional[int] = None
    ) -> None:
        """Handles inline keyboard callback events."""
        await self.answer_callback_query(callback_id, "Memproses aksi...")

        action_parts = data.split(":", 1)
        action = action_parts[0]
        target_id = action_parts[1] if len(action_parts) > 1 else ""

        if action == "summarize":
            email_item = gmail_service.get_email_details(target_id)
            if email_item:
                summary = ai_helper.summarize_text(email_item["body"])
                resp = (
                    f"⚡ <b>Ringkasan AI Email #{target_id}</b>\n"
                    f"<b>Subjek:</b> {email_item['subject']}\n\n"
                    f"{summary}"
                )
                await self.send_message(chat_id, resp)
            else:
                await self.send_message(chat_id, f"❌ Email #{target_id} tidak ditemukan.")

        elif action == "draft":
            email_item = gmail_service.get_email_details(target_id)
            if email_item:
                draft = ai_helper.draft_reply(email_item["subject"], email_item["body"])
                resp = (
                    f"📝 <b>Draf Balasan AI untuk #{target_id}:</b>\n\n"
                    f"<code>{draft}</code>"
                )
                await self.send_message(chat_id, resp)

        elif action == "read":
            success = gmail_service.mark_as_read(target_id)
            if success:
                await self.send_message(chat_id, f"✅ Email ID <code>{target_id}</code> ditandai telah dibaca.")
            else:
                await self.send_message(chat_id, f"⚠️ Gagal menandai email ID <code>{target_id}</code>.")

        elif action == "refresh":
            await self.handle_command(chat_id, "/unread")

    def _build_email_card(self, email_item: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Constructs visually appealing HTML card with actionable inline buttons."""
        text = (
            f"📨 <b>{email_item['subject']}</b>\n"
            f"👤 <i>Dari: {email_item['from']}</i>\n"
            f"📅 <code>{email_item.get('date', 'Hari ini')}</code>\n\n"
            f"💬 {email_item['snippet']}..."
        )
        eid = email_item["id"]
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "⚡ Ringkas AI", "callback_data": f"summarize:{eid}"},
                    {"text": "📝 Draf Balasan", "callback_data": f"draft:{eid}"}
                ],
                [
                    {"text": "✅ Tandai Dibaca", "callback_data": f"read:{eid}"}
                ]
            ]
        }
        return text, keyboard


telegram_handler = TelegramHandler()
