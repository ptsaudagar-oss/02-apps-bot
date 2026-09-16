"""
Enterprise Privacy Enclave and PII Redaction Module.
Provides cryptographic sanitization, PII masking, and strict boundary isolation
for the Master Owner Account (kafnun84@gmail.com).

Security Mandates (SOUL.md §4 + USER-v2.md §3):
  1. Zero Public Dispatch: Emails from or concerning kafnun84@gmail.com are never broadcast
     to public chat channels, group topics, or external webhook relays.
  2. PII Redaction: Automatically masks NIK/KTP, credit card numbers, passwords, OTPs,
     and private tokens prior to AI processing or logging.
  3. Owner-Only Direct Alerting: Only forwarded to the designated Owner Private Chat ID
     with mandatory Human-in-the-Loop (HITL) gate authorization for actionable requests.
"""

import re
from typing import Dict, Any
from core.logger import setup_logger

logger = setup_logger("PRIVACY_ENCLAVE")

# Enclave Protected Identity Constants
MASTER_OWNER_EMAIL = "kafnun84@gmail.com"
B2B_OPERATIONS_EMAIL = "pt.saudagar@gmail.com"
ECOMMERCE_STORE_EMAIL = "8m.shop.online@gmail.com"

# PII Regex Detection Patterns
RE_CREDIT_CARD = re.compile(r"\b\d{4}[ -]\d{4}[ -]\d{4}[ -]\d{4}\b")
RE_INDONESIAN_NIK = re.compile(r"\b\d{16}\b")
RE_PASSWORD_KEY = re.compile(r"(?i)\b(?:password|passwd|kata[ _]?sandi|secret|token|api[ _]?key)[\s:=]+([^\s,;]+)")
RE_OTP_CODE = re.compile(r"(?i)\b(?:otp|kode verifikasi|verification code)[\s:=]+(\d{4,8})\b")
RE_PHONE_NUMBER = re.compile(r"\b(?:\+?62|08)[1-9][0-9]{7,11}\b")
RE_EMAIL_ADDRESS = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


class PrivacyEnclave:
    """Enforces zero-leakage enclave policies and cryptographic PII redaction."""

    def __init__(self, owner_email: str = MASTER_OWNER_EMAIL):
        self.owner_email = owner_email.lower().strip()
        self.b2b_email = B2B_OPERATIONS_EMAIL.lower().strip()
        self.store_email = ECOMMERCE_STORE_EMAIL.lower().strip()

    def is_owner_account(self, email_address: str) -> bool:
        """Verifies if an email address belongs to the Master Owner Account."""
        if not email_address:
            return False
        return self.owner_email in email_address.lower()

    def is_b2b_account(self, email_address: str) -> bool:
        """Verifies if an email address belongs to the B2B Corporate Account."""
        if not email_address:
            return False
        return self.b2b_email in email_address.lower()

    def is_ecommerce_account(self, email_address: str) -> bool:
        """Verifies if an email address belongs to the E-Commerce Store Account."""
        if not email_address:
            return False
        return self.store_email in email_address.lower()

    def should_broadcast_to_public(self, email_from: str, email_to: str = "") -> bool:
        """
        Enforces Zero Public Dispatch mandate:
        NEVER broadcast emails from or to kafnun84@gmail.com to public channels.
        """
        if self.is_owner_account(email_from) or self.is_owner_account(email_to):
            logger.warning(
                f"[ENCLAVE ZERO-BROADCAST ENFORCED] Email involving owner {self.owner_email} "
                f"is strictly barred from public channel broadcasting."
            )
            return False
        return True

    def redact_pii(self, text: str) -> str:
        """
        Scans text and redacts sensitive PII information with cryptographic tokens.
        Preserves grammatical readability while shielding private financial/personal data.
        """
        if not text:
            return ""

        sanitized = text
        redactions_count = 0

        # 1. Redact NIK / KTP Numbers (16 contiguous digits) first
        if RE_INDONESIAN_NIK.search(sanitized):
            redactions_count += len(RE_INDONESIAN_NIK.findall(sanitized))
            sanitized = RE_INDONESIAN_NIK.sub("[REDACTED_NIK_KTP]", sanitized)

        # 2. Redact Credit Card Numbers (Formatted with space/dash or 16-digit cards)
        if RE_CREDIT_CARD.search(sanitized):
            redactions_count += len(RE_CREDIT_CARD.findall(sanitized))
            sanitized = RE_CREDIT_CARD.sub("[REDACTED_CREDIT_CARD]", sanitized)

        # 3. Redact Passwords / Secret Keys
        def _mask_password(match):
            prefix = match.group(0).split(match.group(1))[0]
            return f"{prefix}[REDACTED_SECRET]"
        if RE_PASSWORD_KEY.search(sanitized):
            redactions_count += len(RE_PASSWORD_KEY.findall(sanitized))
            sanitized = RE_PASSWORD_KEY.sub(_mask_password, sanitized)

        # 4. Redact OTP Codes
        def _mask_otp(match):
            prefix = match.group(0).split(match.group(1))[0]
            return f"{prefix}[REDACTED_OTP]"
        if RE_OTP_CODE.search(sanitized):
            redactions_count += len(RE_OTP_CODE.findall(sanitized))
            sanitized = RE_OTP_CODE.sub(_mask_otp, sanitized)

        if redactions_count > 0:
            try:
                from core.telemetry import telemetry_hub
                telemetry_hub.record_pii_redaction(redactions_count)
            except Exception:
                pass

        return sanitized

    def sanitize_email_payload(self, email_item: Dict[str, Any]) -> Dict[str, Any]:
        """Creates an enclave-sanitized copy of an email item."""
        sanitized = dict(email_item)
        is_owner = self.is_owner_account(sanitized.get("from", "")) or self.is_owner_account(sanitized.get("to", ""))

        if is_owner:
            sanitized["enclave_protected"] = True
            sanitized["privacy_level"] = "CRITICAL_PRIVATE"
            # Apply strict redaction to subject, snippet, and body
            sanitized["subject"] = self.redact_pii(sanitized.get("subject", ""))
            sanitized["snippet"] = self.redact_pii(sanitized.get("snippet", ""))
            sanitized["body"] = self.redact_pii(sanitized.get("body", ""))
        else:
            sanitized["enclave_protected"] = False
            sanitized["privacy_level"] = "OPERATIONAL"
            # General redaction for credit cards and passwords
            sanitized["snippet"] = self.redact_pii(sanitized.get("snippet", ""))
            sanitized["body"] = self.redact_pii(sanitized.get("body", ""))

        return sanitized

    def get_account_category(self, account_email: str) -> Dict[str, str]:
        """Classifies account role, routing target, and security level."""
        acc = account_email.lower().strip()
        if self.is_owner_account(acc):
            return {
                "account": MASTER_OWNER_EMAIL,
                "role": "Master Administrator & System Owner",
                "routing": "OWNER_PRIVATE_DIRECT_ONLY",
                "tag": "[🔒 PRIVACY ENCLAVE]",
                "hitl_required": True,
                "public_dispatch": False,
            }
        elif self.is_ecommerce_account(acc):
            return {
                "account": ECOMMERCE_STORE_EMAIL,
                "role": "E-Commerce & Retail Store Operations",
                "routing": "TELEGRAM_STORE_TOPIC_AND_WHATSAPP",
                "tag": "[🛒 E-COMMERCE]",
                "hitl_required": False,
                "public_dispatch": True,
            }
        else:
            return {
                "account": B2B_OPERATIONS_EMAIL,
                "role": "Primary B2B & Enterprise Operations",
                "routing": "TELEGRAM_B2B_TOPIC_AND_WHATSAPP",
                "tag": "[🏢 B2B CORPORATE]",
                "hitl_required": False,
                "public_dispatch": True,
            }


privacy_enclave = PrivacyEnclave()
