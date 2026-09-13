"""
Local Configuration for WhatsApp Bot Module.
"""

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.config import settings

# WhatsApp API & Webhook Configuration
WHATSAPP_VERIFY_TOKEN = settings.WHATSAPP_VERIFY_TOKEN
WHATSAPP_ACCESS_TOKEN = settings.WHATSAPP_ACCESS_TOKEN
WHATSAPP_PHONE_NUMBER_ID = settings.WHATSAPP_PHONE_NUMBER_ID
WHATSAPP_API_VERSION = settings.WHATSAPP_API_VERSION
WHATSAPP_GATEWAY_URL = settings.WHATSAPP_GATEWAY_URL

WHATSAPP_PROVIDER_PRIMARY = settings.WHATSAPP_PROVIDER_PRIMARY
WHATSAPP_LOCAL_GATEWAY_URL = settings.WHATSAPP_LOCAL_GATEWAY_URL
WHATSAPP_FAILOVER_TO_LOCAL = settings.WHATSAPP_FAILOVER_TO_LOCAL

# Server settings
SERVER_HOST = settings.WHATSAPP_SERVER_HOST
SERVER_PORT = settings.WHATSAPP_SERVER_PORT


def get_whatsapp_config():
    """Returns sanitized configuration dictionary."""
    return {
        "verify_token_set": bool(WHATSAPP_VERIFY_TOKEN),
        "access_token_set": bool(WHATSAPP_ACCESS_TOKEN),
        "phone_number_id_set": bool(WHATSAPP_PHONE_NUMBER_ID),
        "gateway_url": WHATSAPP_GATEWAY_URL,
        "api_version": WHATSAPP_API_VERSION,
        "primary_provider": WHATSAPP_PROVIDER_PRIMARY,
        "local_gateway_url": WHATSAPP_LOCAL_GATEWAY_URL,
        "failover_to_local": WHATSAPP_FAILOVER_TO_LOCAL,
        "server_host": SERVER_HOST,
        "server_port": SERVER_PORT,
    }
