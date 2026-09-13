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
        WHATSAPP_ACCESS_TOKEN,
        WHATSAPP_PHONE_NUMBER_ID,
        SERVER_HOST,
        SERVER_PORT
    )

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


@app.get("/", tags=["Health"])
async def root():
    """Health check and service status."""
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
    logger.info(f"Received webhook verification challenge. Mode: {hub_mode}")

    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verification challenge passed successfully.")
        return Response(content=hub_challenge, media_type="text/plain", status_code=200)

    logger.warning("Webhook verification failed: Token mismatch or invalid mode.")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification token mismatch")


@app.post("/webhook", tags=["Webhook"])
async def handle_webhook(request: Request):
    """
    Receives incoming WhatsApp events (messages, button clicks, status updates).
    """
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Invalid JSON received at webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    messages = whatsapp_handler.parse_incoming_webhook(payload)
    for msg in messages:
        # Asynchronously process each message
        asyncio.create_task(whatsapp_handler.process_message(msg))

    return {"status": "EVENT_RECEIVED", "processed_count": len(messages)}


@app.post("/api/send", tags=["API"])
async def send_direct_message(req: SendMessageRequest):
    """
    External programmatic endpoint to trigger outbound WhatsApp message.
    """
    success = await whatsapp_handler.send_message(req.to, req.message)
    if success:
        return {"status": "success", "recipient": req.to}
    raise HTTPException(status_code=500, detail="Failed to dispatch WhatsApp message")


class WhatsAppBotEngine(BaseBotEngine):
    """Lifecycle engine for WhatsApp Bot service."""

    def __init__(self):
        super().__init__("WHATSAPP_BOT")
        self.server: uvicorn.Server = None

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
        """Starts uvicorn server for WhatsApp webhook."""
        if self._is_running:
            logger.warning("WhatsApp Bot server is already running.")
            return

        self._is_running = True
        logger.info(f"Starting WhatsApp Bot Server on {SERVER_HOST}:{SERVER_PORT}...")

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
        if self.server:
            self.server.should_exit = True
        await whatsapp_handler.client.aclose()
        logger.info("WhatsApp Bot Server stopped cleanly.")


bot_engine = WhatsAppBotEngine()


def run_standalone():
    """CLI runner."""
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)


if __name__ == "__main__":
    run_standalone()
