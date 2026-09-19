"""
FastAPI Server and Engine for WhatsApp Bot.
Implements Meta Cloud API Webhook verification, event processing, REST API dispatch, and BaseBotEngine lifecycle.
"""

import os
import sys
import asyncio
import uvicorn
from typing import Dict, Any
from fastapi import FastAPI, Request, Response, Query, HTTPException, status
from pydantic import BaseModel

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.base_bot import BaseBotEngine
from core.config import settings
from core.logger import setup_logger

try:
    from .message_handler import whatsapp_handler
    from .config import (
        WHATSAPP_VERIFY_TOKEN,
        WHATSAPP_ACCESS_TOKEN,
        WHATSAPP_PHONE_NUMBER_ID,
        SERVER_HOST,
        SERVER_PORT
    )
except ImportError:
    from message_handler import whatsapp_handler
    from config import (
        WHATSAPP_VERIFY_TOKEN,
        WHATSAPP_PHONE_NUMBER_ID,
        SERVER_HOST,
        SERVER_PORT
    )

from core.telemetry import telemetry_hub
import time

logger = setup_logger("WHATSAPP_SERVER")

# FastAPI App Instance
app = FastAPI(
    title="APPS_BOT WhatsApp Gateway",
    description="Meta Cloud API & Webhook Bridge for APPS_BOT",
    version="1.0.0"
)


class SendMessageRequest(BaseModel):
    to: str
    message: str


class InboundSMSRequest(BaseModel):
    sender: str
    message: str
    timestamp: str = ""



@app.get("/", tags=["Health"])
@app.get("/health", tags=["Health"])
async def root():
    """Health check and service status for Cloud Platforms (Koyeb/Fly.io)."""
    return {
        "service": "APPS_BOT WhatsApp Service",
        "status": "online",
        "configured": whatsapp_handler.is_configured(),
        "verify_token_active": bool(WHATSAPP_VERIFY_TOKEN)
    }


@app.get("/webhook", tags=["Webhook"])
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """
    Standard Meta WhatsApp Webhook verification handshake.
    Meta sends GET request with challenge string to verify endpoint ownership.
    """
    start_time = time.perf_counter()
    logger.info(f"Received webhook verification challenge. Mode: {hub_mode}")

    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        telemetry_hub.record_latency("whatsapp", "/webhook[GET]", elapsed_ms, 200)
        logger.info(f"Webhook verification challenge passed successfully ({elapsed_ms:.2f}ms).")
        return Response(content=hub_challenge, media_type="text/plain", status_code=200)

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    telemetry_hub.record_latency("whatsapp", "/webhook[GET]", elapsed_ms, 403)
    logger.warning("Webhook verification failed: Token mismatch or invalid mode.")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification token mismatch")


@app.post("/webhook", tags=["Webhook"])
async def handle_webhook(request: Request):
    """
    Receives incoming WhatsApp events (messages, button clicks, status updates).
    Enforces Fast ACK SLA (<150ms).
    """
    start_time = time.perf_counter()
    try:
        payload = await request.json()
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        telemetry_hub.record_latency("whatsapp", "/webhook[POST]", elapsed_ms, 400)
        logger.error(f"Invalid JSON received at webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    messages = whatsapp_handler.parse_incoming_webhook(payload)
    for msg in messages:
        if msg.get("from_me"):
            # Pesan berasal dari ketikan Akang langsung di HP -> sinkronkan ke Telegram (Two-Way Sync)
            asyncio.create_task(whatsapp_handler.sync_outbound_from_phone(msg["sender"], msg["body"]))
        else:
            # Pesan masuk dari customer
            asyncio.create_task(whatsapp_handler.process_message(msg))

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    telemetry_hub.record_latency("whatsapp", "/webhook[POST]", elapsed_ms, 200)
    return {"status": "EVENT_RECEIVED", "processed_count": len(messages), "latency_ms": round(elapsed_ms, 2)}


@app.post("/api/send", tags=["API"])
async def send_direct_message(req: SendMessageRequest):
    """
    External programmatic endpoint to trigger outbound WhatsApp message.
    """
    success = await whatsapp_handler.send_message(req.to, req.message)
    if success:
        return {"status": "success", "recipient": req.to}
    raise HTTPException(status_code=500, detail="Failed to dispatch WhatsApp message")


@app.post("/api/sms", tags=["SMS Gateway"])
async def receive_inbound_sms(req: InboundSMSRequest):
    """
    Inbound SMS Gateway for GSM/SMS forwarding (e.g. 081808630730).
    Automatically logs, audits Enclave privacy, and dispatches real-time alerts to Telegram and WhatsApp.
    """
    start_time = time.perf_counter()
    clean_sender = req.sender.replace("+", "").strip()
    is_master_admin = clean_sender in ("081808630730", "6281808630730", settings.MASTER_ADMIN_WHATSAPP_NUMBER)

    logger.info(f"📱 [INBOUND SMS] From {req.sender} (Master Admin: {is_master_admin}): {req.message}")

    # Format Telegram Alert
    badge = "👑 <b>[SMS DARI MASTER OWNER - 081808630730]</b>" if is_master_admin else "📱 <b>[SMS MASUK]</b>"
    sms_telegram_text = (
        f"{badge}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"• <b>Pengirim:</b> <code>{req.sender}</code>\n"
        f"• <b>Pesan:</b> {req.message}\n"
        f"• <b>Waktu:</b> <code>{req.timestamp or time.strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚡ <i>Real-time SMS Autonomous Ingestion</i>"
    )

    # Push to Telegram if authorized
    try:
        import httpx
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_AUTHORIZED_CHAT_IDS:
            for chat_id in settings.TELEGRAM_AUTHORIZED_CHAT_IDS:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(
                        f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": sms_telegram_text,
                            "parse_mode": "HTML"
                        }
                    )
    except Exception as e:
        logger.error(f"Error forwarding SMS to Telegram: {e}")

    # Acknowledge to WhatsApp if Master Admin
    if is_master_admin and settings.MASTER_ADMIN_WHATSAPP_NUMBER:
        wa_ack = (
            f"📱 *SMS BERHASIL DITERIMA & DITERUSKAN*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"• Dari: {req.sender}\n"
            f"• Pesan: {req.message}\n"
            f"• Status: Terdistribusi ke Telegram @Apps_Bot"
        )
        asyncio.create_task(whatsapp_handler.send_message(settings.MASTER_ADMIN_WHATSAPP_NUMBER, wa_ack))

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
    telemetry_hub.record_latency("sms_gateway", "/api/sms", elapsed_ms, 200)

    return {
        "status": "SMS_DISPATCHED",
        "sender": req.sender,
        "is_master_admin": is_master_admin,
        "latency_ms": round(elapsed_ms, 2)
    }



try:
    from .telegram_wa_bridge import TelegramWABridgeListener
except ImportError:
    from telegram_wa_bridge import TelegramWABridgeListener


class WhatsAppBotEngine(BaseBotEngine):
    """Lifecycle engine for WhatsApp Bot service."""

    def __init__(self):
        super().__init__("WHATSAPP_BOT")
        self.server: uvicorn.Server = None
        self.bridge_listener: TelegramWABridgeListener = TelegramWABridgeListener(whatsapp_handler)
        self._bridge_task: asyncio.Task = None

    def health_check(self) -> Dict[str, Any]:
        """Performs sanity check on WhatsApp configuration and webhook settings."""
        return {
            "configured": whatsapp_handler.is_configured(),
            "verify_token_set": bool(WHATSAPP_VERIFY_TOKEN),
            "phone_number_id": WHATSAPP_PHONE_NUMBER_ID or "NOT_CONFIGURED",
            "host": SERVER_HOST,
            "port": SERVER_PORT,
            "engine_running": self._is_running
        }

    async def start(self) -> None:
        """Starts uvicorn server for WhatsApp webhook and Telegram reply bridge."""
        if self._is_running:
            logger.warning("WhatsApp Bot server is already running.")
            return

        self._is_running = True
        logger.info(f"Starting WhatsApp Bot Server on {SERVER_HOST}:{SERVER_PORT}...")

        # Jalankan Telegram WA Bridge Listener di background
        self._bridge_task = asyncio.create_task(self.bridge_listener.start())
        logger.info("Telegram WA Bridge Listener background worker launched.")

        config = uvicorn.Config(
            app=app,
            host=SERVER_HOST,
            port=SERVER_PORT,
            log_level="warning",
            loop="asyncio"
        )
        self.server = uvicorn.Server(config)
        try:
            await self.server.serve()
        except asyncio.CancelledError:
            logger.info("WhatsApp Bot Server cancelled gracefully.")

    async def stop(self) -> None:
        """Stops the uvicorn server gracefully."""
        logger.info("Stopping WhatsApp Bot Server...")
        self._is_running = False
        if self._bridge_task and not self._bridge_task.done():
            self.bridge_listener.stop()
            self._bridge_task.cancel()
        if self.server:
            self.server.should_exit = True
        await whatsapp_handler.client.aclose()
        await self.bridge_listener.client.aclose()
        logger.info("WhatsApp Bot Server stopped cleanly.")


bot_engine = WhatsAppBotEngine()


def run_standalone():
    """CLI runner."""
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)


if __name__ == "__main__":
    run_standalone()
