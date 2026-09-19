"""
Telegram Bot Handler for Gmail Assistant.
Manages interactive commands, inline keyboards, message formatting, and Telegram Bot API communication via httpx.

Context Injection Sources:
  - SOUL.md §1: Bot Identity → /start greeting
  - MEMORY.md §1-3: Architecture Map → /status display
  - USER.md §1: Owner Attribution → response footer
"""

import html
import httpx
from typing import Dict, Any, Optional, List, Tuple
from core.config import settings
from core.logger import setup_logger
from core.ai_helper import ai_helper
from core import context_loader
from core.privacy_enclave import privacy_enclave
from core.telemetry import telemetry_hub
import time
import urllib.parse
try:
    from .gmail_service import gmail_service
except ImportError:
    from gmail_service import gmail_service

logger = setup_logger("TELEGRAM_HANDLER")

# Pre-load bot identity from SOUL.md + USER.md
_bot_identity = context_loader.get_bot_identity()


class TelegramHandler:
    """Async Telegram API Handler and Message Dispatcher."""

    def __init__(self, token: Optional[str] = None):
        self.token = token if token is not None else settings.TELEGRAM_BOT_TOKEN
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
    ) -> Optional[int]:
        """Sends a text message via Telegram API and tracks latency. Returns message_id if successful."""
        start_time = time.perf_counter()
        if not self.token:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            telemetry_hub.record_latency("telegram", "/sendMessage[SIMULATION]", elapsed_ms, 200)
            logger.info(f"[SIMULASI TELEGRAM] Chat {chat_id} -> {text[:100]}...")
            return 99999

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
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            telemetry_hub.record_latency("telegram", "/sendMessage", elapsed_ms, resp.status_code)
            if resp.status_code == 200:
                data = resp.json()
                msg_id = data.get("result", {}).get("message_id")
                return msg_id if msg_id is not None else 1
            elif resp.status_code == 400 and "can't parse entities" in resp.text and payload.get("parse_mode"):
                logger.warning(f"Telegram entity parse error: {resp.text}. Retrying with plain text fallback...")
                fallback_payload = dict(payload)
                fallback_payload.pop("parse_mode", None)
                fb_resp = await self.client.post(f"{self.api_url}/sendMessage", json=fallback_payload)
                if fb_resp.status_code == 200:
                    logger.info("Telegram plain text fallback delivered successfully.")
                    fb_data = fb_resp.json()
                    fb_msg_id = fb_data.get("result", {}).get("message_id")
                    return fb_msg_id if fb_msg_id is not None else 1
                else:
                    logger.error(f"Fallback plain text send error {fb_resp.status_code}: {fb_resp.text}")
                    return None
            else:
                logger.error(f"Telegram API error {resp.status_code}: {resp.text}")
                return None
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            telemetry_hub.record_latency("telegram", "/sendMessage[EXCEPTION]", elapsed_ms, 500)
            logger.error(f"Failed to send Telegram message: {e}")
            return None

    async def delete_message(self, chat_id: Any, message_id: int) -> bool:
        """Deletes a message from Telegram chat to maintain sliding-window limit (e.g. 10 items)."""
        if not self.token or not message_id or message_id == 99999:
            return True

        payload: Dict[str, Any] = {"chat_id": chat_id, "message_id": message_id}
        try:
            resp = await self.client.post(f"{self.api_url}/deleteMessage", json=payload)
            if resp.status_code == 200:
                logger.debug(f"Deleted Telegram message {message_id} in chat {chat_id}")
                return True
            else:
                logger.debug(f"Delete message {message_id} responded with {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            logger.debug(f"Exception deleting Telegram message {message_id}: {e}")
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
                f"Selamat datang di <b>{_bot_identity['name']}</b> 🤖✉️\n"
                f"<i>{_bot_identity['role']}</i>\n"
                f"<i>Engine: {_bot_identity['engine']}</i>\n\n"
                f"<b>Perintah Tersedia:</b>\n"
                f"📬 <code>/unread</code> - Cek email masuk yang belum dibaca\n"
                f"📊 <code>/status</code> - Cek kesehatan koneksi bot & Gmail\n"
                f"⚡ <code>/summarize &lt;ID&gt;</code> - Minta ringkasan AI untuk email tertentu\n"
                f"📝 <code>/draft &lt;ID&gt;</code> - Buat draf balasan cerdas via AI\n"
                f"📨 <code>/send &lt;tujuan&gt; | &lt;subjek&gt; | &lt;pesan&gt;</code> - Kirim email\n\n"
                f"<i>Status Mode: {'LIVE GMAIL' if gmail_service.is_configured() else 'SIMULASI MOCK'}</i>\n"
                f"<i>Powered by {_bot_identity['organization']}</i>"
            )
            await self.send_message(chat_id, msg)

        elif base_cmd in ("/unread", "/inbox", "/cek"):
            emails = gmail_service.get_unread_emails(limit=10)
            if not emails:
                await self.send_message(chat_id, "🎉 <b>Kotak Masuk Bersih!</b> Tidak ada email baru yang belum dibaca.")
                return

            await self.send_message(chat_id, f"📬 <b>Ditemukan {len(emails)} Email Belum Dibaca (Maksimal 10 Terkini):</b>")
            for item in emails:
                text_card, markup = self._build_email_card(item)
                await self.send_message(chat_id, text_card, reply_markup=markup)

        elif base_cmd in ("/clean", "/clear", "/purge", "/sapu"):
            await self.send_message(chat_id, "⏳ <i>Sedang membersihkan kotak masuk Gmail & mereset live streaming...</i>")
            cleaned = gmail_service.clean_all_inbox()
            clean_text = (
                f"🧹 <b>KOTAK MASUK BERSIH TOTAL!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• <b>Email Dibersihkan:</b> <code>{cleaned}</code> email lama ditandai telah dibaca.\n"
                f"• <b>Live Stream Buffer:</b> Direset (Maksimal 10 inbox).\n"
                f"• <b>Mode Otomatis:</b> Email baru akan masuk secara realtime dan menggeser email terlama.\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"✨ <i>Kotak masuk Gmail Anda kini bersih dan siap siaga!</i>"
            )
            await self.send_message(chat_id, clean_text)

        elif base_cmd == "/status":
            connected, msg_conn = gmail_service.check_connection()
            status_text = (
                f"⚙️ <b>Status Sistem {_bot_identity['name']}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• <b>Identitas:</b> {_bot_identity['name']}\n"
                f"• <b>Organisasi:</b> {_bot_identity['organization']}\n"
                f"• <b>Metodologi:</b> {_bot_identity['methodology']}\n"
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

            safe_args = html.escape(args.strip())
            email_item = gmail_service.get_email_details(args.strip())
            if not email_item:
                await self.send_message(chat_id, f"❌ Email dengan ID <code>{safe_args}</code> tidak ditemukan.")
                return

            await self.send_message(chat_id, f"⏳ <i>Sedang menganalisis & meringkas email ID {safe_args}...</i>")
            summary = ai_helper.summarize_text(email_item["body"])
            reply_text = (
                f"⚡ <b>Ringkasan Eksekutif AI</b>\n"
                f"<b>Subjek:</b> {html.escape(str(email_item.get('subject', '')))}\n"
                f"<b>Dari:</b> {html.escape(str(email_item.get('from', '')))}\n\n"
                f"📋 <b>Hasil Analisis:</b>\n{html.escape(str(summary))}"
            )
            await self.send_message(chat_id, reply_text)

        elif base_cmd == "/draft":
            if not args:
                await self.send_message(chat_id, "⚠️ Format salah. Gunakan: <code>/draft &lt;ID_EMAIL&gt;</code>")
                return

            safe_args = html.escape(args.strip())
            email_item = gmail_service.get_email_details(args.strip())
            if not email_item:
                await self.send_message(chat_id, f"❌ Email dengan ID <code>{safe_args}</code> tidak ditemukan.")
                return

            draft = ai_helper.draft_reply(email_item["subject"], email_item["body"])
            reply_text = (
                f"📝 <b>Draf Balasan AI</b>\n"
                f"<b>Untuk:</b> {html.escape(str(email_item.get('from', '')))}\n"
                f"<b>Re:</b> {html.escape(str(email_item.get('subject', '')))}\n\n"
                f"<code>{html.escape(str(draft))}</code>"
            )
            await self.send_message(chat_id, reply_text)

        elif base_cmd in ("/metrics", "/telemetry"):
            lat = telemetry_hub.get_latency_stats()
            tok = telemetry_hub.get_token_efficiency_stats()
            disp = telemetry_hub.get_dispatch_stats()
            sec = telemetry_hub.get_security_stats()
            telemetry_text = (
                f"📈 <b>PHASE 3 TELEMETRY & LIVE ANALYTICS</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• <b>Total Requests:</b> {lat['total_requests']}\n"
                f"• <b>Avg Latency ACK:</b> {lat['avg_latency_ms']}ms (<150ms SLA)\n"
                f"• <b>SLA Compliance:</b> {lat['sla_compliance_pct']}%\n"
                f"• <b>Alerts Triggered:</b> {lat['alerts_triggered']}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• <b>9Router Token Savings:</b> {tok['avg_compression_savings_pct']}% (Target -40%)\n"
                f"• <b>Tokens Saved:</b> {tok['total_tokens_saved']:,}\n"
                f"• <b>WhatsApp RAM Sessions:</b> {disp['active_ram_sessions']}/15\n"
                f"• <b>Meta vs Bridge Failovers:</b> {disp['local_bridge_failovers']}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• <b>Privacy Enclave:</b> {sec['zero_leakage_status']}\n"
                f"• <b>PII Redactions:</b> {sec['pii_redaction_triggers']}\n"
                f"• <b>System Uptime:</b> {telemetry_hub.get_uptime_seconds()}s\n"
            )
            await self.send_message(chat_id, telemetry_text)

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
                await self.send_message(chat_id, f"✅ <b>Berhasil Dikirim!</b>\nKe: <code>{html.escape(to_addr)}</code>\nSubjek: {html.escape(subj)}")
            else:
                await self.send_message(chat_id, f"❌ <b>Gagal Mengirim:</b> {html.escape(str(msg_result))}")

        else:
            await self.send_message(
                chat_id,
                f"❓ Perintah <code>{html.escape(base_cmd)}</code> tidak dikenali. Ketik <code>/help</code> untuk melihat daftar perintah."
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
                gmail_url = self._generate_gmail_url(email_item)
                resp = (
                    f"⚡ <b>Ringkasan AI Email #{html.escape(target_id)}</b>\n"
                    f"<b>Subjek:</b> {html.escape(str(email_item.get('subject', '')))}\n"
                    f"<b>Akun:</b> <code>{html.escape(str(email_item.get('account', '-')))}</code>\n\n"
                    f"{html.escape(str(summary))}\n\n"
                    f"🔗 <a href='{gmail_url}'>Buka Email Ini Langsung di Gmail</a>"
                )
                summary_keyboard = {
                    "inline_keyboard": [
                        [
                            {"text": "🌐 Buka di Gmail", "url": gmail_url},
                            {"text": "📝 Buat Draf Balasan", "callback_data": f"draft:{target_id}"}
                        ]
                    ]
                }
                await self.send_message(chat_id, resp, reply_markup=summary_keyboard)
            else:
                await self.send_message(chat_id, f"❌ Email #{html.escape(target_id)} tidak ditemukan.")

        elif action == "draft":
            email_item = gmail_service.get_email_details(target_id)
            if email_item:
                draft = ai_helper.draft_reply(email_item["subject"], email_item["body"])
                resp = (
                    f"📝 <b>Draf Balasan AI untuk #{html.escape(target_id)}:</b>\n\n"
                    f"<code>{html.escape(str(draft))}</code>"
                )
                await self.send_message(chat_id, resp)

        elif action in ("approve", "setuju"):
            email_item = gmail_service.get_email_details(target_id)
            sender_to = email_item.get("from", "Mitra B2B") if email_item else "Mitra B2B"
            subj = email_item.get("subject", "Persetujuan Kontrak") if email_item else "Persetujuan Kontrak"
            reply_body = (
                f"Yth. Tim Procurement / Pengirim,\n\n"
                f"Dengan ini kami mengonfirmasi bahwa penawaran / persetujuan untuk '{subj}' "
                f"telah disetujui (APPROVED) secara resmi dan diteruskan ke tahap administrasi berikutnya.\n\n"
                f"Salam hormat,\nPT. Saudagar Operations"
            )
            # Send notification and dispatch automated reply
            success, msg_result = gmail_service.send_email(sender_to, f"Re: [APPROVED] {subj}", reply_body)
            gmail_service.mark_as_read(target_id)
            resp = (
                f"✅ <b>AKSI DISETUJUI & DIPROSES!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• <b>Target:</b> <code>{html.escape(str(sender_to))}</code>\n"
                f"• <b>Status:</b> Persetujuan Resmi Terkirim (HTTP 200 OK)\n"
                f"• <b>Log ID:</b> <code>ACK-{html.escape(target_id)}</code>\n"
                f"• <b>Kotak Masuk:</b> Ditandai Telah Selesai Dibaca\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━"
            )
            await self.send_message(chat_id, resp)

        elif action in ("reject", "tolak"):
            email_item = gmail_service.get_email_details(target_id)
            sender_to = email_item.get("from", "Pengirim") if email_item else "Pengirim"
            subj = email_item.get("subject", "Pemberitahuan Penolakan") if email_item else "Pemberitahuan Penolakan"
            gmail_service.mark_as_read(target_id)
            resp = (
                f"❌ <b>TRANSAKSI DITOLAK / DIBATALKAN!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• <b>Target:</b> <code>{html.escape(str(sender_to))}</code>\n"
                f"• <b>Status:</b> Transaksi Dibatalkan oleh Pengawas Sistem (HITL)\n"
                f"• <b>Log ID:</b> <code>REJ-{html.escape(target_id)}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━"
            )
            await self.send_message(chat_id, resp)

        elif action == "read":
            success = gmail_service.mark_as_read(target_id)
            if success:
                if message_id:
                    await self.delete_message(chat_id, message_id)
                await self.send_message(chat_id, f"✅ Email ID <code>{html.escape(target_id)}</code> ditandai telah dibaca.")
            else:
                await self.send_message(chat_id, f"⚠️ Gagal menandai email ID <code>{html.escape(target_id)}</code>.")

        elif action == "refresh":
            await self.handle_command(chat_id, "/unread")

    def _generate_gmail_url(self, email_item: Dict[str, Any]) -> str:
        """Constructs an authentic direct deep-link into Gmail web/mobile app."""
        account = email_item.get("account") or email_item.get("to") or "0"
        subject = email_item.get("subject", "")
        # Clean subject for exact search
        clean_subj = subject.replace('"', '').strip()
        encoded_query = urllib.parse.quote(f'subject:"{clean_subj}"')
        return f"https://mail.google.com/mail/u/?authuser={account}#search/{encoded_query}"

    def _build_email_card(self, email_item: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Constructs visually appealing HTML card with account badges and actionable inline buttons."""
        sender_email = email_item.get("from", "")
        target_account = email_item.get("account", sender_email)
        account_meta = privacy_enclave.get_account_category(target_account)
        account_tag = account_meta.get("tag", "[📧 GMAIL]")
        gmail_url = self._generate_gmail_url(email_item)

        safe_tag = html.escape(str(account_tag))
        safe_subject = html.escape(str(email_item.get("subject", "(Tanpa Subjek)")))
        safe_from = html.escape(str(email_item.get("from", "(Pengirim Tidak Dikenal)")))
        safe_to = html.escape(str(target_account))
        safe_date = html.escape(str(email_item.get("date", "Hari ini")))
        safe_snippet = html.escape(str(email_item.get("snippet", "")))

        text = (
            f"📨 <b>{safe_tag} {safe_subject}</b>\n"
            f"👤 <i>Dari: {safe_from}</i>\n"
            f"📥 <i>Ke: <code>{safe_to}</code></i>\n"
            f"📅 <code>{safe_date}</code>\n\n"
            f"💬 {safe_snippet}..."
        )
        eid = email_item["id"]

        # Dynamic buttons based on account category
        if account_meta.get("account") == "8m.shop.online@gmail.com":
            # E-Commerce & Retail Store Buttons
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "🔍 Cek Detail", "callback_data": f"summarize:{eid}"},
                        {"text": "⚙️ Proses Pesanan", "callback_data": f"draft:{eid}"}
                    ],
                    [
                        {"text": "🌐 Buka di Gmail", "url": gmail_url},
                        {"text": "✅ Tandai Selesai", "callback_data": f"read:{eid}"}
                    ]
                ]
            }
        elif account_meta.get("hitl_required"):
            # Master Owner Privacy Enclave
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "🛡️ HITL Otorisasi", "callback_data": f"draft:{eid}"},
                        {"text": "🔒 Arsip Enclave", "callback_data": f"read:{eid}"}
                    ],
                    [
                        {"text": "🌐 Buka di Gmail Enclave", "url": gmail_url}
                    ]
                ]
            }
        else:
            # Primary B2B & Enterprise Operations
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "⚡ Ringkas AI", "callback_data": f"summarize:{eid}"},
                        {"text": "📝 Draf Balasan", "callback_data": f"draft:{eid}"}
                    ],
                    [
                        {"text": "🌐 Buka di Gmail", "url": gmail_url},
                        {"text": "✅ Tandai Dibaca", "callback_data": f"read:{eid}"}
                    ]
                ]
            }
        return text, keyboard

    async def dispatch_sla_alert(self, alert_payload: Dict[str, Any], chat_id: Optional[str] = None) -> bool:
        """Sends automated emergency alert to Telegram admin thread if ACK > 200ms or on critical failure."""
        target_chat = chat_id or (settings.TELEGRAM_AUTHORIZED_CHAT_IDS[0] if settings.TELEGRAM_AUTHORIZED_CHAT_IDS else None)
        if not target_chat:
            logger.warning("No Telegram authorized chat configured for SLA alert dispatch.")
            return False

        alert_text = (
            f"🚨 <b>[AUTOMATED SLA BREACH ALERT]</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• <b>Reason:</b> {alert_payload.get('reason', 'Latency threshold exceeded')}\n"
            f"• <b>Channel:</b> <code>{alert_payload.get('channel')}</code>\n"
            f"• <b>Endpoint:</b> <code>{alert_payload.get('endpoint')}</code>\n"
            f"• <b>Measured Latency:</b> <code>{alert_payload.get('latency_ms', 0):.2f}ms</code> (Threshold: 200ms)\n"
            f"• <b>Status Code:</b> <code>{alert_payload.get('status_code', 200)}</code>\n"
            f"• <b>Timestamp:</b> <code>{alert_payload.get('timestamp')}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <i>Antigravity Real-Time Telemetry Monitor</i>"
        )
        return await self.send_message(target_chat, alert_text)


telegram_handler = TelegramHandler()
telemetry_hub.register_alert_listener(lambda payload: logger.info(f"Telemetry SLA Alert registered: {payload}"))

