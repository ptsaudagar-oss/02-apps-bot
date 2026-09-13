"""
Local Configuration for Telegram Gmail Bot Module.
Extends master settings with specialized defaults.
"""

import os
from core.config import settings

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Local module defaults
MODULE_DIR = CURRENT_DIR
CREDENTIALS_PATH = os.path.join(MODULE_DIR, "credentials.json")
TOKEN_PATH = os.path.join(MODULE_DIR, "token.json")

# IMAP/SMTP Server Hosts
GMAIL_IMAP_SERVER = "imap.gmail.com"
GMAIL_IMAP_PORT = 993
GMAIL_SMTP_SERVER = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587

# Export configuration helper
def get_telegram_config():
    return {
        "bot_token": settings.TELEGRAM_BOT_TOKEN,
        "authorized_chat_ids": settings.TELEGRAM_AUTHORIZED_CHAT_IDS,
        "polling_interval": settings.TELEGRAM_POLLING_INTERVAL,
        "gmail_email": settings.GMAIL_USER_EMAIL,
        "gmail_auth_mode": settings.GMAIL_AUTH_MODE,
        "check_interval": settings.GMAIL_CHECK_INTERVAL_SECONDS,
        "has_credentials_json": os.path.exists(CREDENTIALS_PATH)
    }
