"""
Configuration Module for APPS_BOT.
Implements localized path resolution and centralized environment variable loading.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Path & Environment Localization per Global User Rules
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
ENV_PATH = os.path.join(ROOT_DIR, ".env")
LOG_DIR = os.path.join(ROOT_DIR, "logs")

# Load .env if present
if os.path.exists(ENV_PATH):
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

# Ensure logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)


class Settings:
    """Master Application Settings with localized defaults."""

    # Project metadata
    PROJECT_NAME: str = "APPS_BOT Multi-System Framework"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    # Localized Paths
    BASE_DIR: str = ROOT_DIR
    LOGS_DIR: str = LOG_DIR
    TELEGRAM_BOT_DIR: str = os.path.join(ROOT_DIR, "00-TELEGRAM_BOT")
    WHATSAPP_BOT_DIR: str = os.path.join(ROOT_DIR, "01-WHATSAPP_BOT")

    # AI Configuration (Google GenAI)
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

    # Telegram Bot Settings
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_AUTHORIZED_CHAT_IDS: list[str] = [
        cid.strip() for cid in os.getenv("TELEGRAM_AUTHORIZED_CHAT_IDS", "").split(",") if cid.strip()
    ]
    TELEGRAM_POLLING_INTERVAL: int = int(os.getenv("TELEGRAM_POLLING_INTERVAL", "5"))

    # Gmail Integration Settings
    GMAIL_USER_EMAIL: str = os.getenv("GMAIL_USER_EMAIL", "")
    GMAIL_APP_PASSWORD: str = os.getenv("GMAIL_APP_PASSWORD", "")
    GMAIL_AUTH_MODE: str = os.getenv("GMAIL_AUTH_MODE", "app_password").lower()  # 'app_password' or 'oauth2'
    GMAIL_CREDENTIALS_JSON: str = os.getenv(
        "GMAIL_CREDENTIALS_JSON", 
        os.path.join(ROOT_DIR, "00-TELEGRAM_BOT", "00-G-MAIL_BOT", "credentials.json")
    )
    GMAIL_CHECK_INTERVAL_SECONDS: int = int(os.getenv("GMAIL_CHECK_INTERVAL_SECONDS", "60"))

    # WhatsApp Bot Settings
    WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "APPS_BOT_WHATSAPP_SECRET_TOKEN")
    WHATSAPP_ACCESS_TOKEN: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    WHATSAPP_API_VERSION: str = os.getenv("WHATSAPP_API_VERSION", "v21.0")
    WHATSAPP_GATEWAY_URL: str = os.getenv("WHATSAPP_GATEWAY_URL", "https://graph.facebook.com")
    WHATSAPP_SERVER_HOST: str = os.getenv("WHATSAPP_SERVER_HOST", "127.0.0.1")
    WHATSAPP_SERVER_PORT: int = int(os.getenv("WHATSAPP_SERVER_PORT", "8080"))
    WHATSAPP_PROVIDER_PRIMARY: str = os.getenv("WHATSAPP_PROVIDER_PRIMARY", "meta").lower()
    WHATSAPP_LOCAL_GATEWAY_URL: str = os.getenv("WHATSAPP_LOCAL_GATEWAY_URL", "http://127.0.0.1:3000/api/send")
    WHATSAPP_FAILOVER_TO_LOCAL: bool = os.getenv("WHATSAPP_FAILOVER_TO_LOCAL", "true").lower() in ("true", "1", "yes")

    @classmethod
    def get_summary(cls) -> dict:
        """Get sanitized configuration summary for health check and diagnostics."""
        return {
            "PROJECT_NAME": cls.PROJECT_NAME,
            "ROOT_DIR": cls.BASE_DIR,
            "LOGS_DIR": cls.LOGS_DIR,
            "DEBUG": cls.DEBUG,
            "TELEGRAM_CONFIGURED": bool(cls.TELEGRAM_BOT_TOKEN),
            "GMAIL_CONFIGURED": bool(cls.GMAIL_USER_EMAIL and (cls.GMAIL_APP_PASSWORD or os.path.exists(cls.GMAIL_CREDENTIALS_JSON))),
            "WHATSAPP_CONFIGURED": bool(cls.WHATSAPP_ACCESS_TOKEN and cls.WHATSAPP_PHONE_NUMBER_ID),
            "WHATSAPP_FAILOVER_ENABLED": cls.WHATSAPP_FAILOVER_TO_LOCAL,
            "WHATSAPP_PRIMARY_PROVIDER": cls.WHATSAPP_PROVIDER_PRIMARY,
            "GEMINI_CONFIGURED": bool(cls.GEMINI_API_KEY),
        }


settings = Settings()
