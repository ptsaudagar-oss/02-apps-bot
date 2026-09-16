"""
Core Shared Module for APPS_BOT Framework.
Provides centralized configuration, logging, bot base contracts, AI helpers, context loader, and privacy enclave.
"""

from core.config import settings, ROOT_DIR
from core.logger import setup_logger, Colors
from core.base_bot import BaseBotEngine, zero_crash
from core.privacy_enclave import privacy_enclave, PrivacyEnclave

__version__ = "1.0.0"
