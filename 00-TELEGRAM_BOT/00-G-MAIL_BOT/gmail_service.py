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
try:
    from .config import GMAIL_IMAP_SERVER, GMAIL_IMAP_PORT, GMAIL_SMTP_SERVER, GMAIL_SMTP_PORT
except ImportError:
    from config import GMAIL_IMAP_SERVER, GMAIL_IMAP_PORT, GMAIL_SMTP_SERVER, GMAIL_SMTP_PORT

logger = setup_logger("GMAIL_SERVICE")


class GmailService:
    """Enterprise Gmail Service supporting IMAP/SMTP SSL and Mock Simulation."""

    def __init__(self):
        self.email_address = settings.GMAIL_USER_EMAIL
        self.app_password = settings.GMAIL_APP_PASSWORD
        self._mock_data: List[Dict[str, Any]] = self._generate_mock_emails()

    def is_configured(self) -> bool:
        """Returns True if real Gmail credentials are provided."""
        return bool(self.email_address and self.app_password)

    def check_connection(self) -> Tuple[bool, str]:
        """Tests live IMAP connection to Gmail."""
        if not self.is_configured():
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
        """Fetches unread emails from Gmail INBOX, or simulated items if in mock mode."""
        if not self.is_configured():
            logger.info("Operating in SIMULATION mode. Returning mock unread inbox.")
            return [e for e in self._mock_data if not e["is_read"]][:limit]

        unread_list: List[Dict[str, Any]] = []
        try:
            mail = imaplib.IMAP4_SSL(GMAIL_IMAP_SERVER, GMAIL_IMAP_PORT, timeout=15)
            mail.login(self.email_address, self.app_password)
            mail.select("INBOX")

            status, search_data = mail.search(None, "UNSEEN")
            if status != "OK" or not search_data[0]:
                mail.logout()
                return []

            email_ids = search_data[0].split()
            # Fetch latest emails first
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

                        unread_list.append({
                            "id": e_id.decode("utf-8", errors="ignore"),
                            "subject": subject,
                            "from": sender,
                            "date": date_str,
                            "snippet": body[:180].replace("\n", " ").strip(),
                            "body": body,
                            "is_read": False,
                        })

            mail.logout()
        except Exception as e:
            logger.error(f"Error fetching unread Gmail messages: {e}")

        return unread_list

    def get_email_details(self, email_id: str) -> Optional[Dict[str, Any]]:
        """Gets full details of a specific email by ID."""
        if not self.is_configured():
            for item in self._mock_data:
                if item["id"] == str(email_id):
                    return item
            return None

        try:
            mail = imaplib.IMAP4_SSL(GMAIL_IMAP_SERVER, GMAIL_IMAP_PORT, timeout=15)
            mail.login(self.email_address, self.app_password)
            mail.select("INBOX")

            status, data = mail.fetch(email_id.encode(), "(RFC822)")
            if status != "OK":
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
                    return {
                        "id": str(email_id),
                        "subject": subject,
                        "from": sender,
                        "date": date_str,
                        "snippet": body[:180].replace("\n", " ").strip(),
                        "body": body,
                        "is_read": False
                    }
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

    def send_email(self, to_email: str, subject: str, content: str) -> Tuple[bool, str]:
        """Sends an email via Gmail SMTP SSL."""
        if not self.is_configured():
            logger.info(f"[SIMULASI] Email terkirim ke {to_email} | Subjek: {subject}")
            return True, "Simulated email successfully dispatched (mock mode)."

        try:
            msg = MIMEMultipart()
            msg["From"] = self.email_address
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(content, "plain", "utf-8"))

            server = smtplib.SMTP(GMAIL_SMTP_SERVER, GMAIL_SMTP_PORT, timeout=15)
            server.starttls()
            server.login(self.email_address, self.app_password)
            server.send_message(msg)
            server.quit()
            return True, f"Email berhasil dikirim ke {to_email}"
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False, str(e)

    def _decode_mime_words(self, s: str) -> str:
        """Decodes MIME encoded header fields."""
        decoded_words = []
        for word, encoding in decode_header(s):
            if isinstance(word, bytes):
                try:
                    decoded_words.append(word.decode(encoding or "utf-8", errors="ignore"))
                except Exception:
                    decoded_words.append(word.decode("latin1", errors="ignore"))
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
        """Generates realistic test email items for simulation and automated tests."""
        return [
            {
                "id": "101",
                "subject": "Laporan Mingguan Sprint Antigravity AI Bot",
                "from": "pm-lead@corporate-tech.com",
                "date": datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0700"),
                "snippet": "Halo Tim, berikut rangkuman capaian sprint pekan ini: modul Telegram Bot dan WhatsApp Bot telah siap...",
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
                "subject": "Tagihan Server Cloud Hosting Bulan Ini",
                "from": "billing@cloudservice.net",
                "date": datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0700"),
                "snippet": "Faktur Anda untuk periode berjalan sebesar Rp 150.000 telah terbit dan jatuh tempo...",
                "body": (
                    "Yth. Pelanggan,\n\n"
                    "Tagihan cloud Anda untuk bulan berjalan telah terbit.\n"
                    "Total Biaya: Rp 150.000\n"
                    "Jatuh Tempo: 20 September 2026\n"
                    "Silakan selesaikan pembayaran sebelum tanggal jatuh tempo.\n"
                    "Terima kasih."
                ),
                "is_read": False
            },
            {
                "id": "103",
                "subject": "Undangan Rapat Koordinasi Arsitektur AI",
                "from": "chief-architect@enterprise.id",
                "date": datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0700"),
                "snippet": "Diharapkan kehadirannya pada sesi evaluasi keselarasan arsitektur mikroservis hari Selasa jam 10.00 WIB...",
                "body": (
                    "Selamat Siang,\n\n"
                    "Kami mengundang Anda dalam agenda evaluasi implementasi sistem bot:\n"
                    "Waktu: Selasa, 10:00 WIB\n"
                    "Lokasi: Google Meet Virtual Room\n"
                    "Agenda: Review QC Protocol, Error Handling, dan Deployment Plan.\n"
                    "Mohon konfirmasi kehadiran.\nSalam Hormat."
                ),
                "is_read": True
            }
        ]


gmail_service = GmailService()
