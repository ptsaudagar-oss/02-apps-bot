"""
Main Entrypoint and Engine for Telegram Gmail Bot.
Implements BaseBotEngine lifecycle, asynchronous long polling, and proactive inbox push monitoring.
"""

import asyncio
import signal
import sys
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.base_bot import BaseBotEngine
from core.config import settings
from core.logger import setup_logger

try:
    from .telegram_handler import telegram_handler
    from .gmail_service import gmail_service
except ImportError:
    from telegram_handler import telegram_handler
    from gmail_service import gmail_service

logger = setup_logger("TG_GMAIL_BOT")


class TelegramGmailBotEngine(BaseBotEngine):
    """Production-grade Telegram Gmail Assistant Engine."""

    def __init__(self):
        super().__init__("TELEGRAM_GMAIL_BOT")
        self._notified_email_ids: Set[str] = set()
        self._polling_task: asyncio.Task = None
        self._inbox_watcher_task: asyncio.Task = None
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

    async def start(self) -> None:
        """Starts asynchronous long-polling and background inbox monitor."""
        if self._is_running:
            logger.warning("Bot is already running.")
            return

        self._is_running = True
        logger.info("Starting Telegram Gmail Bot Engine...")

        health = self.health_check()
        logger.info(f"Health check status: {health}")

        # Spawn concurrent tasks
        self._polling_task = asyncio.create_task(self._run_polling_loop())
        self._inbox_watcher_task = asyncio.create_task(self._run_inbox_watcher())

        try:
            await asyncio.gather(self._polling_task, self._inbox_watcher_task)
        except asyncio.CancelledError:
            logger.info("Bot engine tasks cancelled gracefully.")

    async def stop(self) -> None:
        """Stops tasks and terminates connections."""
        logger.info("Stopping Telegram Gmail Bot Engine...")
        self._is_running = False

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
        """Monitors inbox periodically and pushes alerts for brand-new unread emails."""
        interval = max(settings.GMAIL_CHECK_INTERVAL_SECONDS, 10)
        logger.info(f"Gmail Inbox proactive watcher started (Interval: {interval}s).")

        # Prime initial notified set to avoid blasting notifications on first startup
        initial_unreads = gmail_service.get_unread_emails(limit=20)
        for e in initial_unreads:
            self._notified_email_ids.add(e["id"])

        while self._is_running:
            try:
                await asyncio.sleep(interval)
                unreads = gmail_service.get_unread_emails(limit=10)

                for item in unreads:
                    if item["id"] not in self._notified_email_ids:
                        self._notified_email_ids.add(item["id"])
                        logger.info(f"Proactive alert: New unread email detected ID {item['id']}")

                        # Broadcast to all authorized chat IDs
                        card_text, markup = telegram_handler._build_email_card(item)
                        header_alert = "🚨 <b>EMAIL BARU MASUK!</b> 📬\n\n" + card_text
                        for chat_id in settings.TELEGRAM_AUTHORIZED_CHAT_IDS:
                            await telegram_handler.send_message(chat_id, header_alert, reply_markup=markup)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Gmail watcher loop: {e}")


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
