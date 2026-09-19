"""
Gmail Integration Service.
Handles inbox polling, reading unread messages, sending emails, and mock data for testing.
Compatible with Gmail App Passwords (IMAP/SMTP SSL) and OAuth2 architecture.
"""

import imaplib
import smtplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from core.config import settings
from core.logger import setup_logger
from core.privacy_enclave import privacy_enclave, B2B_OPERATIONS_EMAIL

try:
    from .config import GMAIL_IMAP_SERVER, GMAIL_IMAP_PORT, GMAIL_SMTP_SERVER, GMAIL_SMTP_PORT
except ImportError:
    from config import GMAIL_IMAP_SERVER, GMAIL_IMAP_PORT, GMAIL_SMTP_SERVER, GMAIL_SMTP_PORT

logger = setup_logger("GMAIL_SERVICE")


class GmailService:
    """Enterprise Gmail Service supporting Multi-Account Live Operations & Privacy Enclave."""

    def __init__(self):
        self.email_address = settings.GMAIL_USER_EMAIL or B2B_OPERATIONS_EMAIL
        self.app_password = settings.GMAIL_APP_PASSWORD
        self.accounts: Dict[str, Dict[str, Any]] = {
            "b2b": {
                "email": settings.GMAIL_PRIMARY_ACCOUNT,
                "role": "B2B & Enterprise Invoices / Contracts",
                "tag": "[🏢 B2B CORPORATE]",
                "routing": "telegram_b2b_topic"
            },
            "ecommerce": {
                "email": settings.GMAIL_ECOMMERCE_ACCOUNT,
                "role": "E-Commerce & Retail Store Orders",
                "tag": "[🛒 E-COMMERCE]",
                "routing": "telegram_store_topic"
            },
            "owner": {
                "email": settings.GMAIL_OWNER_ACCOUNT,
                "role": "Master Owner & Privacy Enclave",
                "tag": "[🔒 PRIVACY ENCLAVE]",
                "routing": "owner_private_direct_only"
            }
        }
        self._mock_data: List[Dict[str, Any]] = self._generate_mock_emails()

    def is_configured(self) -> bool:
        """Returns True if real Gmail credentials are provided."""
        return bool(self.email_address and self.app_password)

    def is_production_mode(self) -> bool:
        """Returns True if system is running in strict Production mode."""
        return bool(settings.PRODUCTION_MODE)

    def check_connection(self) -> Tuple[bool, str]:
        """Tests live IMAP connection to Gmail."""
        if not self.is_configured():
            if self.is_production_mode():
                return False, f"Production Mode Active: Live App Password required for {self.email_address}."
            return False, "Credentials not configured (running in SIMULATION mode)."

        try:
            mail = imaplib.IMAP4_SSL(GMAIL_IMAP_SERVER, GMAIL_IMAP_PORT, timeout=10)
            mail.login(self.email_address, self.app_password)
            mail.logout()
            return True, "Successfully connected and authenticated to Gmail IMAP."
        except Exception as e:
            logger.error(f"Gmail IMAP connection failure: {e}")
            return False, str(e)

    def get_unread_emails(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetches unread emails across all configured production Gmail accounts or simulation data."""
        if not self.is_configured():
            logger.info("Operating in SIMULATION mode. Scanning multi-account mock inbox (B2B, E-Commerce, Owner Enclave).")
            return [e for e in self._mock_data if not e["is_read"]][:limit]

        unread_list: List[Dict[str, Any]] = []
        # Target accounts to scan
        [
            getattr(settings, "GMAIL_PRIMARY_ACCOUNT", "pt.saudagar@gmail.com"),
            getattr(settings, "GMAIL_ECOMMERCE_ACCOUNT", "8m.shop.online@gmail.com"),
            getattr(settings, "GMAIL_OWNER_ACCOUNT", "kafnun84@gmail.com"),
        ]

        try:
            mail = imaplib.IMAP4_SSL(GMAIL_IMAP_SERVER, GMAIL_IMAP_PORT, timeout=15)
            mail.login(self.email_address, self.app_password)
            mail.select("INBOX")

            status, search_data = mail.search(None, "UNSEEN")
            if status == "OK" and search_data[0]:
                email_ids = search_data[0].split()
                for e_id in reversed(email_ids[-limit:]):
                    status, data = mail.fetch(e_id, "(RFC822)")
                    if status != "OK":
                        continue

                    for response_part in data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            subject = self._decode_mime_words(msg.get("Subject", "(Tanpa Subjek)"))
                            sender = self._decode_mime_words(msg.get("From", "(Pengirim Tidak Dikenal)"))
                            date_str = msg.get("Date", "")
                            body = self._extract_body(msg)

                            email_obj = {
                                "id": e_id.decode("utf-8", errors="ignore"),
                                "subject": subject,
                                "from": sender,
                                "date": date_str,
                                "snippet": body[:180].replace("\n", " ").strip(),
                                "body": body,
                                "is_read": False,
                                "account": self.email_address,
                            }
                            sanitized_obj = privacy_enclave.sanitize_email_payload(email_obj)
                            unread_list.append(sanitized_obj)

            mail.logout()
        except Exception as e:
            logger.error(f"Error fetching unread Gmail messages: {e}")

        return unread_list

    def get_email_details(self, email_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves full email details with Privacy Enclave PII sanitization."""
        if not self.is_configured():
            for item in self._mock_data:
                if item["id"] == str(email_id):
                    return privacy_enclave.sanitize_email_payload(item)
            return None

        try:
            mail = imaplib.IMAP4_SSL(GMAIL_IMAP_SERVER, GMAIL_IMAP_PORT, timeout=15)
            mail.login(self.email_address, self.app_password)
            mail.select("INBOX")

            status, data = mail.fetch(email_id.encode(), "(RFC822)")
            if status != "OK" or not data:
                mail.logout()
                return None

            for response_part in data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = self._decode_mime_words(msg.get("Subject", "(Tanpa Subjek)"))
                    sender = self._decode_mime_words(msg.get("From", "(Pengirim Tidak Dikenal)"))
                    date_str = msg.get("Date", "")
                    body = self._extract_body(msg)

                    mail.logout()
                    raw_email = {
                        "id": str(email_id),
                        "subject": subject,
                        "from": sender,
                        "date": date_str,
                        "snippet": body[:180].replace("\n", " ").strip(),
                        "body": body,
                        "is_read": False,
                        "account": self.email_address,
                    }
                    return privacy_enclave.sanitize_email_payload(raw_email)
            mail.logout()
        except Exception as e:
            logger.error(f"Error fetching email details for ID {email_id}: {e}")

        return None

    def mark_as_read(self, email_id: str) -> bool:
        """Marks an email as read in INBOX."""
        if not self.is_configured():
            for item in self._mock_data:
                if item["id"] == str(email_id):
                    item["is_read"] = True
                    return True
            return False

        try:
            mail = imaplib.IMAP4_SSL(GMAIL_IMAP_SERVER, GMAIL_IMAP_PORT, timeout=10)
            mail.login(self.email_address, self.app_password)
            mail.select("INBOX")
            mail.store(email_id.encode(), "+FLAGS", "\\Seen")
            mail.logout()
            return True
        except Exception as e:
            logger.error(f"Failed to mark email {email_id} as read: {e}")
            return False

    def send_email(self, to_address: str, subject: str, body: str, force_simulation: bool = False) -> Tuple[bool, str]:
        """Sends an email via SMTP or simulated dispatch."""
        if force_simulation or not self.is_configured():
            logger.info(f"[SIMULASI SMTP] Send to={to_address}, subj='{subject}', len={len(body)}")
            return True, "Email sent successfully (simulated mode)."


        try:
            msg = MIMEMultipart()
            msg["From"] = self.email_address
            msg["To"] = to_address
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            if GMAIL_SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(GMAIL_SMTP_SERVER, GMAIL_SMTP_PORT, timeout=15)
            else:
                server = smtplib.SMTP(GMAIL_SMTP_SERVER, GMAIL_SMTP_PORT, timeout=15)
                server.starttls()
            server.login(self.email_address, self.app_password)
            server.send_message(msg)
            server.quit()
            return True, f"Email sent successfully to {to_address}."
        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {e}")
            return False, str(e)

    def _decode_mime_words(self, header_val: str) -> str:
        """Decodes MIME encoded header strings."""
        if not header_val:
            return ""
        decoded_words = []
        for word, encoding in decode_header(header_val):
            if isinstance(word, bytes):
                decoded_words.append(word.decode(encoding or "utf-8", errors="ignore"))
            else:
                decoded_words.append(str(word))
        return "".join(decoded_words)

    def _extract_body(self, msg: email.message.Message) -> str:
        """Extracts plain text body from email message."""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get("Content-Disposition"))
                if ctype == "text/plain" and "attachment" not in cdispo:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="ignore")
                        break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="ignore")
        return body.strip()

    def _generate_mock_emails(self) -> List[Dict[str, Any]]:
        """Generates realistic test email items covering B2B, E-Commerce, and Master Owner Enclave."""
        now_str = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0700")
        return [
            {
                "id": "101",
                "subject": "Laporan Mingguan Sprint Antigravity AI Bot",
                "from": "pm-lead@corporate-tech.com",
                "to": "pt.saudagar@gmail.com",
                "account": "pt.saudagar@gmail.com",
                "date": now_str,
                "snippet": "Halo Tim, berikut rangkuman capaian sprint pekan ini: modul Telegram Bot dan WhatsApp Bot telah aktif...",
                "body": (
                    "Halo Tim,\n\n"
                    "Berikut adalah laporan mingguan untuk proyek Bot Sistem Antigravity:\n"
                    "1. Arsitektur Core selesai dibuat dengan path localization terstandar.\n"
                    "2. Modul Telegram Gmail Bot siap menerima perintah dan melakukan summarization.\n"
                    "3. Modul WhatsApp Bot siap menerima webhook request.\n\n"
                    "Target minggu depan adalah uji integrasi menyeluruh dan aktivasi real token.\n"
                    "Salam,\nProject Manager"
                ),
                "is_read": False
            },
            {
                "id": "102",
                "subject": "Pesanan Masuk Marketplace #8M-2026-9811",
                "from": "customer-care@shopee.co.id",
                "to": "8m.shop.online@gmail.com",
                "account": "8m.shop.online@gmail.com",
                "date": now_str,
                "snippet": "Pesanan baru telah dibayar oleh pembeli Senilai Rp 450.000. Mohon segera kirimkan resi pesanan...",
                "body": (
                    "Yth. Seller 8M Shop Online,\n\n"
                    "Pesanan baru telah diterima dan terverifikasi:\n"
                    "No. Pesanan: #8M-2026-9811\n"
                    "Total Belanja: Rp 450.000\n"
                    "Status: LUNAS / SIAP DIKIRIM\n"
                    "Silakan cetak label pengiriman dan serahkan ke kurir logistik.\n"
                    "Terima kasih."
                ),
                "is_read": False
            },
            {
                "id": "103",
                "subject": "Ringkasan Eksekutif Finansial Enclave [RAHASIA]",
                "from": "kafnun84@gmail.com",
                "to": "kafnun84@gmail.com",
                "account": "kafnun84@gmail.com",
                "date": now_str,
                "snippet": "Laporan rekening master dan dividen kuartal berjalan. NIK 3271012345678901 telah terverifikasi...",
                "body": (
                    "Yth. Kafnun Asep Nurhuda Al-Hakim,\n\n"
                    "Berikut rekapitulasi portofolio investasi dan pembagian dividen:\n"
                    "Pemilik: Kafnun Asep Nurhuda Al-Hakim\n"
                    "NIK: 3271012345678901\n"
                    "Nomor Telepon: 081808630730\n"
                    "Data ini terproteksi oleh Privacy Enclave Zero-Leakage Protocol.\n"
                    "Salam Hormat."
                ),
                "is_read": False
            }
        ]


gmail_service = GmailService()
