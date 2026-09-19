"""
Main Entrypoint and Engine for Telegram Gmail Bot.
Implements BaseBotEngine lifecycle, asynchronous long polling, and proactive inbox push monitoring.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Set, Dict, Any, List, Optional

CATEGORY_STREAM_LIMIT = 10
TOTAL_STREAM_LIMIT = 20
ALLOWED_CATEGORIES = ["PRIMARY", "UPDATES"]
STREAM_STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stream_state.json")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.base_bot import BaseBotEngine
from core.config import settings
from core.logger import setup_logger
from core.privacy_enclave import privacy_enclave

try:
    from .telegram_handler import telegram_handler
    from .gmail_service import gmail_service
except ImportError:
    from telegram_handler import telegram_handler
    from gmail_service import gmail_service

# Load WhatsApp Handler cleanly via importlib to avoid config.py module collision
whatsapp_handler = None
try:
    import importlib.util
    wa_handler_path = os.path.join(PROJECT_ROOT, "01-WHATSAPP_BOT", "message_handler.py")
    if os.path.exists(wa_handler_path):
        spec = importlib.util.spec_from_file_location("wa_handler_module", wa_handler_path)
        wa_mod = importlib.util.module_from_spec(spec)
        # Ensure 01-WHATSAPP_BOT is temporarily in sys.path during its module load only
        wa_bot_dir = os.path.join(PROJECT_ROOT, "01-WHATSAPP_BOT")
        was_in_path = wa_bot_dir in sys.path
        if not was_in_path:
            sys.path.append(wa_bot_dir)
        try:
            spec.loader.exec_module(wa_mod)
            whatsapp_handler = getattr(wa_mod, "whatsapp_handler", None)
        finally:
            if not was_in_path and wa_bot_dir in sys.path:
                sys.path.remove(wa_bot_dir)
except Exception:
    whatsapp_handler = None

logger = setup_logger("TG_GMAIL_BOT")


class TelegramGmailBotEngine(BaseBotEngine):
    """Production-grade Telegram Gmail Assistant Engine with 10 Primary + 10 Update (Total 20) Sliding-Window Live Stream."""

    def __init__(self):
        super().__init__("TELEGRAM_GMAIL_BOT")
        self._notified_email_ids: Set[str] = set()
        self._stream_window: List[Dict[str, Any]] = []
        self._polling_task: asyncio.Task = None
        self._inbox_watcher_task: asyncio.Task = None
        self._http_server = None
        self._last_update_id = 0
        self._load_stream_state()

    def _load_stream_state(self) -> None:
        """Loads persisted active stream window state."""
        if os.path.exists(STREAM_STATE_PATH):
            try:
                with open(STREAM_STATE_PATH, "r", encoding="utf-8") as f:
                    self._stream_window = json.load(f)
                    for entry in self._stream_window:
                        if "email_id" in entry:
                            self._notified_email_ids.add(str(entry["email_id"]))
                logger.info(f"Loaded {len(self._stream_window)} active stream window card(s) from state.")
            except Exception as e:
                logger.debug(f"Could not load stream state: {e}")
                self._stream_window = []

    def _save_stream_state(self) -> None:
        """Persists active stream window state."""
        try:
            with open(STREAM_STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(self._stream_window, f, indent=2)
        except Exception as e:
            logger.debug(f"Could not save stream state: {e}")

    def _record_stream_entry(self, email_id: str, chat_id: Any, message_id: int, subject: str, category: str = "PRIMARY") -> None:
        """Records a new message card in the active sliding-window buffer with category tagging."""
        cat = str(category).upper()
        if cat in ("UPDATE", "UPDATES"):
            cat = "UPDATES"
        else:
            cat = "PRIMARY"

        self._stream_window = [e for e in self._stream_window if str(e.get("email_id")) != str(email_id)]
        self._stream_window.append({
            "email_id": str(email_id),
            "chat_id": chat_id,
            "message_id": message_id,
            "subject": subject,
            "category": cat,
            "timestamp": time.time()
        })
        self._save_stream_state()

    async def _enforce_stream_window(self) -> None:
        """
        Maintains maximum 10 unread items per category (PRIMARY and UPDATES)
        and maximum 20 items overall in the live stream by evicting oldest.
        """
        for cat in ALLOWED_CATEGORIES:
            cat_entries = [e for e in self._stream_window if e.get("category", "PRIMARY").upper() == cat]
            while len(cat_entries) > CATEGORY_STREAM_LIMIT:
                oldest = cat_entries.pop(0)
                self._stream_window = [e for e in self._stream_window if e.get("email_id") != oldest["email_id"]]
                logger.info(
                    f"🔄 [SLIDING FIFO] Evicting oldest [{cat}] email ID {oldest['email_id']} "
                    f"('{oldest['subject']}') to maintain {CATEGORY_STREAM_LIMIT} cards for {cat}."
                )
                await telegram_handler.delete_message(oldest["chat_id"], oldest["message_id"])
                gmail_service.mark_as_read(oldest["email_id"])
                self._save_stream_state()

        # Global safeguard: total window must not exceed TOTAL_STREAM_LIMIT (20)
        while len(self._stream_window) > TOTAL_STREAM_LIMIT:
            oldest = self._stream_window.pop(0)
            logger.info(
                f"🔄 [GLOBAL FIFO] Evicting oldest overall email ID {oldest['email_id']} "
                f"to maintain {TOTAL_STREAM_LIMIT} max total cards."
            )
            await telegram_handler.delete_message(oldest["chat_id"], oldest["message_id"])
            gmail_service.mark_as_read(oldest["email_id"])
            self._save_stream_state()

    def health_check(self) -> Dict[str, Any]:
        """Validates configuration tokens, Gmail status, and engine readiness."""
        gmail_conn, gmail_info = gmail_service.check_connection()
        return {
            "telegram_token_present": bool(settings.TELEGRAM_BOT_TOKEN),
            "gmail_account": settings.GMAIL_USER_EMAIL or "NOT_CONFIGURED",
            "gmail_connected": gmail_conn,
            "gmail_details": gmail_info,
            "authorized_chats": len(settings.TELEGRAM_AUTHORIZED_CHAT_IDS),
            "engine_running": self._is_running
        }

    async def _handle_http_health_check(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handles incoming HTTP GET health probes from Cloud Platforms / Container environments."""
        try:
            await reader.readline()
            while True:
                header = await reader.readline()
                if not header or header == b"\r\n":
                    break

            health_data = self.health_check()
            body_dict = {
                "status": "healthy" if health_data.get("engine_running") else "standby",
                "service": "TELEGRAM_GMAIL_BOT",
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat(),
                "details": health_data
            }
            body = json.dumps(body_dict, indent=2).encode("utf-8")
            response = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: application/json\r\n"
                b"Content-Length: " + str(len(body)).encode("utf-8") + b"\r\n"
                b"Connection: close\r\n\r\n" + body
            )
            writer.write(response)
            await writer.drain()
        except Exception as e:
            logger.debug(f"HTTP health probe handled with notice: {e}")
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def start(self) -> None:
        """Starts asynchronous long-polling, background inbox monitor, and Cloud HTTP health server."""
        if self._is_running:
            logger.warning("Bot is already running.")
            return

        self._is_running = True
        logger.info("Starting Telegram Gmail Bot Engine...")

        health = self.health_check()
        logger.info(f"Health check status: {health}")

        # Cloud / Container HTTP Health Check Support (Fly.io / Koyeb / Docker / Serverless)
        port_env = os.getenv("PORT") or os.getenv("TELEGRAM_BOT_PORT")
        if not port_env and (os.getenv("FLY_APP_NAME") or os.getenv("FLY_ALLOC_ID")):
            port_env = "8080"
        elif not port_env and (os.getenv("KOYEB_APP_NAME") or os.getenv("KOYEB_SERVICE_NAME")):
            port_env = "8000"
        if port_env:
            try:
                port = int(port_env)
                self._http_server = await asyncio.start_server(
                    self._handle_http_health_check, "0.0.0.0", port
                )
                logger.info(f"🌐 Cloud HTTP Health Check server active on 0.0.0.0:{port}")
            except Exception as e:
                logger.warning(f"Could not bind Cloud HTTP server on port {port_env}: {e}")

        # Spawn concurrent tasks
        self._polling_task = asyncio.create_task(self._run_polling_loop())
        self._inbox_watcher_task = asyncio.create_task(self._run_inbox_watcher())

        try:
            await asyncio.gather(self._polling_task, self._inbox_watcher_task)
        except asyncio.CancelledError:
            logger.info("Bot engine tasks cancelled gracefully.")

    async def stop(self) -> None:
        """Stops tasks, terminates HTTP server, and terminates connections."""
        logger.info("Stopping Telegram Gmail Bot Engine...")
        self._is_running = False

        if self._http_server:
            try:
                self._http_server.close()
                await self._http_server.wait_closed()
                logger.info("Cloud HTTP Health Check server closed.")
            except Exception as e:
                logger.warning(f"Error closing HTTP health check server: {e}")

        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
        if self._inbox_watcher_task and not self._inbox_watcher_task.done():
            self._inbox_watcher_task.cancel()

        await telegram_handler.client.aclose()
        logger.info("Telegram Gmail Bot Engine stopped cleanly.")

    async def _run_polling_loop(self) -> None:
        """Continuously polls Telegram for incoming messages and button callbacks."""
        logger.info("Telegram polling loop started.")
        while self._is_running:
            try:
                updates = await telegram_handler.get_updates(offset=self._last_update_id + 1, timeout=10)
                for update in updates:
                    self._last_update_id = update["update_id"]

                    # 1. Handle incoming text message / command
                    if "message" in update and "text" in update["message"]:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        text = msg["text"]
                        user_name = msg.get("from", {}).get("first_name", "Pengguna")
                        logger.info(f"Incoming message from chat {chat_id}: {text}")

                        # If user commands clean/clear/purge, delete all active stream messages from chat
                        if text.strip().lower() in ("/clean", "/clear", "/purge", "/sapu"):
                            logger.info("Sweeping active stream cards from chat...")
                            for entry in self._stream_window:
                                await telegram_handler.delete_message(entry["chat_id"], entry["message_id"])
                            self._stream_window = []
                            self._notified_email_ids.clear()
                            self._save_stream_state()

                        await telegram_handler.handle_command(chat_id, text, user_name)

                    # 2. Handle inline button callback query
                    elif "callback_query" in update:
                        cb = update["callback_query"]
                        cb_id = cb["id"]
                        data = cb.get("data", "")
                        chat_id = cb["message"]["chat"]["id"] if "message" in cb else None
                        msg_id = cb["message"]["message_id"] if "message" in cb else None
                        logger.info(f"Inline callback received from chat {chat_id}: {data}")

                        # If user clicks 'read:ID', remove from active sliding-window buffer
                        if data.startswith("read:") and msg_id:
                            self._stream_window = [e for e in self._stream_window if e.get("message_id") != msg_id]
                            self._save_stream_state()

                        if chat_id:
                            await telegram_handler.handle_callback(cb_id, chat_id, data, msg_id)

                await asyncio.sleep(settings.TELEGRAM_POLLING_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Telegram polling loop: {e}")
                await asyncio.sleep(5)

    async def _run_inbox_watcher(self) -> None:
        """Monitors inbox periodically with real-time sliding window (10 Primary + 10 Update = Total 20 items)."""
        interval = max(int(getattr(settings, "GMAIL_CHECK_INTERVAL_SECONDS", 15) or 15), 5)
        logger.info(
            f"Gmail Inbox proactive watcher started (Interval: {interval}s). "
            f"Real-time sliding-window ({CATEGORY_STREAM_LIMIT} Primary + {CATEGORY_STREAM_LIMIT} Update = Max {TOTAL_STREAM_LIMIT} items) ACTIVE."
        )

        # 1. Clean old backlog in Gmail, keeping only the 10 newest unread per category
        cleaned_backlog = gmail_service.clean_inbox_backlog(keep_latest=CATEGORY_STREAM_LIMIT, categories=["primary", "updates"])
        if cleaned_backlog > 0:
            logger.info(f"🧹 Cleaned {cleaned_backlog} old backlog emails in Gmail upon watcher startup.")

        # 2. Scan initial unreads
        try:
            initial_unreads = gmail_service.get_unread_emails_by_category(categories=["primary", "updates"], limit_per_category=CATEGORY_STREAM_LIMIT)
            logger.info(f"Initial inbox scan found {len(initial_unreads)} unread email(s) across PRIMARY & UPDATES.")
            for item in initial_unreads:
                if item["id"] not in self._notified_email_ids:
                    self._notified_email_ids.add(item["id"])
                    await self._dispatch_dual_channel_alert(item, is_initial=True)
        except Exception as e:
            logger.error(f"Error during initial inbox scan: {e}")

        # 3. Continuous watcher loop
        while self._is_running:
            try:
                await asyncio.sleep(interval)
                unreads = gmail_service.get_unread_emails_by_category(categories=["primary", "updates"], limit_per_category=CATEGORY_STREAM_LIMIT)

                for item in unreads:
                    if item["id"] not in self._notified_email_ids:
                        self._notified_email_ids.add(item["id"])
                        logger.info(f"⚡ [REAL-TIME PUSH] New unread [{item.get('category')}] email detected ID {item['id']} ('{item.get('subject')}')")
                        await self._dispatch_dual_channel_alert(item, is_initial=False)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Gmail watcher loop: {e}")

    async def _dispatch_dual_channel_alert(self, item: Dict[str, Any], is_initial: bool = False) -> None:
        """Dispatches automated alert with sliding-window FIFO buffer (10 Primary + 10 Update = Total 20 items)."""
        sender_addr = item.get("from", "")
        account_addr = item.get("account", "")
        subject = item.get("subject", "(Tanpa Subjek)")
        snippet = item.get("snippet", "")
        eid = item.get("id", "")

        cat = str(item.get("category", "PRIMARY")).upper()
        if cat in ("UPDATE", "UPDATES"):
            cat = "UPDATES"
            cat_badge = "🔔 [UPDATE]"
        else:
            cat = "PRIMARY"
            cat_badge = "⭐️ [PRIMARY]"

        cat_count = sum(1 for e in self._stream_window if e.get("category", "PRIMARY").upper() == cat) + 1
        total_count = len(self._stream_window) + 1

        prefix = "[INBOX SCAN]" if is_initial else "🚨 [REAL-TIME ALERT]"

        # Build WhatsApp Alert Text
        wa_text = (
            f"📬 *{cat_badge} {prefix} EMAIL MASUK*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"• *Kategori:* {cat} (Slot #{min(cat_count, CATEGORY_STREAM_LIMIT)}/{CATEGORY_STREAM_LIMIT})\n"
            f"• *Subjek:* {subject}\n"
            f"• *Pengirim:* {sender_addr}\n"
            f"• *ID:* #{eid}\n"
            f"• *Rangkuman:* {snippet[:120]}...\n\n"
            f"Ketik *menu* atau kelola via Telegram @Apps_Bot"
        )

        # 1. Privacy Enclave Check
        is_public_safe = privacy_enclave.should_broadcast_to_public(sender_addr, account_addr)

        if not is_public_safe:
            logger.info(f"[ENCLAVE DIRECT ROUTING] Email from {sender_addr} isolated to Owner Direct Notification.")
            card_text, markup = telegram_handler._build_email_card(item)
            header_alert = (
                f"🔒 <b>[ENCLAVE PRIVATE ALERT] {prefix} EMAIL OWNER MASUK:</b> 📬\n"
                f"<i>Kategori: {cat} (Slot #{min(cat_count, CATEGORY_STREAM_LIMIT)}/{CATEGORY_STREAM_LIMIT} • Total #{min(total_count, TOTAL_STREAM_LIMIT)}/{TOTAL_STREAM_LIMIT})</i>\n\n"
                + card_text
            )

            # Push to Telegram Owner
            if settings.TELEGRAM_AUTHORIZED_CHAT_IDS:
                owner_chat = settings.TELEGRAM_AUTHORIZED_CHAT_IDS[0]
                msg_id = await telegram_handler.send_message(owner_chat, header_alert, reply_markup=markup)
                if msg_id and msg_id != 99999:
                    self._record_stream_entry(eid, owner_chat, msg_id, subject, category=cat)
                    await self._enforce_stream_window()

            # Push to Master WhatsApp Owner Enclave
            if whatsapp_handler and settings.MASTER_ADMIN_WHATSAPP_NUMBER:
                await whatsapp_handler.send_message(
                    settings.MASTER_ADMIN_WHATSAPP_NUMBER, 
                    f"🔒 *[ENCLAVE OWNER ALERT]*\n" + wa_text
                )
            return

        # 2. Standard Dispatch to Telegram Authorized Chats
        card_text, markup = telegram_handler._build_email_card(item)
        header_alert = (
            f"{cat_badge} <b>{prefix} EMAIL MASUK!</b> 📬\n"
            f"<i>Kategori: {cat} (Slot #{min(cat_count, CATEGORY_STREAM_LIMIT)}/{CATEGORY_STREAM_LIMIT} • Total Live: #{min(total_count, TOTAL_STREAM_LIMIT)}/{TOTAL_STREAM_LIMIT})</i>\n\n"
            + card_text
        )
        for chat_id in settings.TELEGRAM_AUTHORIZED_CHAT_IDS:
            msg_id = await telegram_handler.send_message(chat_id, header_alert, reply_markup=markup)
            if msg_id and msg_id != 99999:
                self._record_stream_entry(eid, chat_id, msg_id, subject, category=cat)
                await self._enforce_stream_window()

        # 3. Direct Dispatch to Master Admin WhatsApp
        if whatsapp_handler and settings.MASTER_ADMIN_WHATSAPP_NUMBER:
            await whatsapp_handler.send_message(settings.MASTER_ADMIN_WHATSAPP_NUMBER, wa_text)


bot_engine = TelegramGmailBotEngine()


async def main():
    """Direct execution runner."""
    try:
        await bot_engine.start()
    except (KeyboardInterrupt, SystemExit):
        await bot_engine.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user.")
