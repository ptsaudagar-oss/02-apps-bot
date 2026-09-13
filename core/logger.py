"""
Logging Module for APPS_BOT.
Provides high-contrast colorized console output and structured rotating file logs.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Windows Console UTF-8 protection
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
from core.config import settings

# ANSI / Colorama codes for high visual contrast
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Foreground colors
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    
    # Background badges
    BG_BLUE = "\033[44m\033[97m"
    BG_GREEN = "\033[42m\033[97m"
    BG_YELLOW = "\033[43m\033[30m"
    BG_RED = "\033[41m\033[97m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter providing high-contrast visual badges for console logs."""

    LEVEL_MAP = {
        logging.DEBUG: (Colors.CYAN, "DEBUG"),
        logging.INFO: (Colors.GREEN, "INFO "),
        logging.WARNING: (Colors.YELLOW, "WARN "),
        logging.ERROR: (Colors.RED, "ERROR"),
        logging.CRITICAL: (f"{Colors.BG_RED}{Colors.BOLD}", "CRIT "),
    }

    def format(self, record: logging.LogRecord) -> str:
        color, badge = self.LEVEL_MAP.get(record.levelno, (Colors.WHITE, record.levelname))
        time_str = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        module_name = f"{Colors.BLUE}[{record.name}]{Colors.RESET}"
        badge_str = f"{color}[{badge}]{Colors.RESET}"
        msg = f"{Colors.WHITE}{record.getMessage()}{Colors.RESET}"

        if record.exc_info:
            msg += f"\n{self.formatException(record.exc_info)}"

        return f"{Colors.DIM}{time_str}{Colors.RESET} {badge_str} {module_name} {msg}"


def setup_logger(name: str = "APPS_BOT") -> logging.Logger:
    """Configures and returns a logger instance with console and file handlers."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level = logging.DEBUG if settings.DEBUG else logging.INFO
    logger.setLevel(level)

    # 1. Console Handler (High-contrast ANSI)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)

    # 2. Rotating File Handler (Clean structured plaintext)
    log_file = os.path.join(settings.LOGS_DIR, "apps_bot.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)-5s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger


# Default global logger
logger = setup_logger("APPS_BOT")
