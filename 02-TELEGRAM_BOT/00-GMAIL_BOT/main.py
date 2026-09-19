"""
Main Entrypoint and Engine for Telegram Gmail Bot.
Implements BaseBotEngine lifecycle, asynchronous long polling, and proactive inbox push monitoring.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Set, Dict, Any

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
    """Production-grade Telegram Gmail Assistant Engine."""

    def __init__(self):
        super().__init__("TELEGRAM_GMAIL_BOT")
        self._notified_email_ids: Set[str] = set()
        self._polling_task: asyncio.Task = None
        self._inbox_watcher_task: asyncio.Task = None
        self._http_server = None
        self._last_update_id = 0

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
                        await telegram_handler.handle_command(chat_id, text, user_name)

                    # 2. Handle inline button callback query
                    elif "callback_query" in update:
                        cb = update["callback_query"]
                        cb_id = cb["id"]
                        data = cb.get("data", "")
                        chat_id = cb["message"]["chat"]["id"] if "message" in cb else None
                        msg_id = cb["message"]["message_id"] if "message" in cb else None
                        logger.info(f"Inline callback received from chat {chat_id}: {data}")
                        if chat_id:
                            await telegram_handler.handle_callback(cb_id, chat_id, data, msg_id)

                await asyncio.sleep(settings.TELEGRAM_POLLING_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Telegram polling loop: {e}")
                await asyncio.sleep(5)

    async def _run_inbox_watcher(self) -> None:
        """Monitors inbox periodically and pushes alerts for unread emails across all accounts to Telegram and WhatsApp in real time."""
        interval = max(int(getattr(settings, "GMAIL_CHECK_INTERVAL_SECONDS", 60) or 60), 5)
        logger.info(f"Gmail Inbox proactive watcher started (Interval: {interval}s). Real-time autonomous push across accounts (pt.saudagar, 8m.shop.online, kafnun84) ACTIVE.")

        # Check existing unreads immediately on start so the bot is NOT static
        try:
            initial_unreads = gmail_service.get_unread_emails(limit=10)
            logger.info(f"Initial inbox check found {len(initial_unreads)} unread email(s).")
            for item in initial_unreads:
                self._notified_email_ids.add(item["id"])
                # Send immediate alert to owner/authorized channels upon engine spin-up
                await self._dispatch_dual_channel_alert(item, is_initial=True)
        except Exception as e:
            logger.error(f"Error during initial inbox scan: {e}")

        while self._is_running:
            try:
                await asyncio.sleep(interval)
                unreads = gmail_service.get_unread_emails(limit=10)

                for item in unreads:
                    if item["id"] not in self._notified_email_ids:
                        self._notified_email_ids.add(item["id"])
                        logger.info(f"⚡ [REAL-TIME PUSH] New unread email detected ID {item['id']} ('{item.get('subject')}')")
                        await self._dispatch_dual_channel_alert(item, is_initial=False)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Gmail watcher loop: {e}")

    async def _dispatch_dual_channel_alert(self, item: Dict[str, Any], is_initial: bool = False) -> None:
        """Dispatches automated alert to Telegram and WhatsApp (Master Admin)."""
        sender_addr = item.get("from", "")
        account_addr = item.get("account", "")
        subject = item.get("subject", "(Tanpa Subjek)")
        snippet = item.get("snippet", "")
        eid = item.get("id", "")

        prefix = "[INBOX SCAN]" if is_initial else "🚨 [REAL-TIME ALERT]"

        # Build WhatsApp Alert Text
        wa_text = (
            f"📬 *{prefix} EMAIL MASUK*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
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
            header_alert = f"🔒 <b>[ENCLAVE PRIVATE ALERT] {prefix} EMAIL OWNER MASUK:</b> 📬\n\n" + card_text

            # Push to Telegram Owner
            if settings.TELEGRAM_AUTHORIZED_CHAT_IDS:
                owner_chat = settings.TELEGRAM_AUTHORIZED_CHAT_IDS[0]
                await telegram_handler.send_message(owner_chat, header_alert, reply_markup=markup)

            # Push to Master WhatsApp Owner Enclave
            if whatsapp_handler and settings.MASTER_ADMIN_WHATSAPP_NUMBER:
                await whatsapp_handler.send_message(
                    settings.MASTER_ADMIN_WHATSAPP_NUMBER, 
                    f"🔒 *[ENCLAVE OWNER ALERT]*\n" + wa_text
                )
            return

        # 2. Standard Dispatch to Telegram Authorized Chats
        card_text, markup = telegram_handler._build_email_card(item)
        header_alert = f"<b>{prefix} EMAIL MASUK!</b> 📬\n\n" + card_text
        for chat_id in settings.TELEGRAM_AUTHORIZED_CHAT_IDS:
            await telegram_handler.send_message(chat_id, header_alert, reply_markup=markup)

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
