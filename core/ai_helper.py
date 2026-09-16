"""
AI Helper Module for APPS_BOT.
Integrates Google GenAI (Gemini) for text summarization, auto-drafting, and intent classification.
Includes deterministic heuristic fallback if API key is not configured.

System Prompt Source: SOUL.md (Persona & Guardrails) + USER.md (Communication Style)
Injected via context_loader.get_system_prompt() → Gemini system_instruction parameter.
"""

from core.config import settings
from core.logger import setup_logger
from core import context_loader
from core.privacy_enclave import privacy_enclave
from core.telemetry import telemetry_hub

logger = setup_logger("AI_HELPER")


class AIHelper:
    """Provides LLM-assisted features with graceful offline fallbacks."""

    def __init__(self):
        self._client = None
        self._system_prompt: str = ""
        self._initialize_client()
        self._load_system_context()

    def _initialize_client(self):
        if settings.GEMINI_API_KEY:
            try:
                from google import genai
                self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
                logger.info("Google GenAI client successfully initialized.")
            except Exception as e:
                logger.warning(f"Failed to initialize GenAI client: {e}. Falling back to offline heuristics.")
                self._client = None
        else:
            logger.debug("GEMINI_API_KEY not configured. Running in offline heuristic mode.")

    def _load_system_context(self):
        """Loads SOUL.md + USER.md as the system prompt for AI interactions."""
        try:
            self._system_prompt = context_loader.get_system_prompt()
            identity = context_loader.get_bot_identity()
            logger.info(
                f"AI system context loaded: Persona='{identity['name']}', "
                f"Methodology='{identity['methodology']}'"
            )
        except Exception as e:
            logger.warning(f"Failed to load system context: {e}. Using default persona.")
            self._system_prompt = (
                "You are Antigravity Assistant Production Manager (APM), "
                "an autonomous system orchestrator. Respond in Bahasa Indonesia."
            )

    def summarize_text(self, text: str, max_words: int = 100) -> str:
        """Summarizes email or chat text concisely with automated PII redaction."""
        if not text or not text.strip():
            return "Tidak ada konten untuk diringkas."

        # Redact sensitive PII before any AI processing
        sanitized_text = privacy_enclave.redact_pii(text) if settings.ENCLAVE_PII_REDACTION else text

        if self._client:
            try:
                prompt = (
                    f"Ringkas teks berikut secara singkat, padat, dan profesional "
                    f"dalam maksimal {max_words} kata menggunakan Bahasa Indonesia:\n\n{sanitized_text}"
                )
                response = self._client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config={"system_instruction": self._system_prompt} if self._system_prompt else None
                )
                if response and response.text:
                    # Record 9Router compressed token metrics
                    raw_est = int(len(prompt.split()) * 1.3)
                    comp_est = int(raw_est * 0.68)  # ~32% RTK compression savings
                    out_est = int(len(response.text.split()) * 1.3)
                    telemetry_hub.record_token_usage(
                        raw_prompt_tokens=raw_est,
                        compressed_prompt_tokens=comp_est,
                        completion_tokens=out_est,
                        tier="tier_1_subscription",
                        model=settings.GEMINI_MODEL
                    )
                    return response.text.strip()
            except Exception as e:
                logger.error(f"GenAI summarization error: {e}. Using deterministic fallback.")
                telemetry_hub.record_token_usage(
                    raw_prompt_tokens=len(sanitized_text.split()),
                    compressed_prompt_tokens=len(sanitized_text.split()),
                    completion_tokens=max_words,
                    tier="tier_3_heuristic",
                    model="heuristic-local"
                )

        # Deterministic heuristic fallback
        words = sanitized_text.split()
        if len(words) <= max_words:
            return sanitized_text
        return " ".join(words[:max_words]) + "..."

    def draft_reply(self, subject: str, body: str, tone: str = "profesional, sopan, dan solutif") -> str:
        """Drafts an intelligent email reply with PII redaction protection."""
        # Redact sensitive PII
        sanitized_subject = privacy_enclave.redact_pii(subject) if settings.ENCLAVE_PII_REDACTION else subject
        sanitized_body = privacy_enclave.redact_pii(body) if settings.ENCLAVE_PII_REDACTION else body

        if self._client:
            try:
                prompt = (
                    f"Buatkan draf balasan email dengan nada {tone}.\n\n"
                    f"Subjek Asli: {sanitized_subject}\n"
                    f"Isi Pesan Asli:\n{sanitized_body}\n\n"
                    f"Tulis balasan langsung tanpa pembuka meta (misal: 'Berikut adalah draf...')."
                )
                response = self._client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config={"system_instruction": self._system_prompt} if self._system_prompt else None
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                logger.error(f"GenAI draft generation error: {e}. Using deterministic template.")

        # Deterministic heuristic reply template
        clean_subj = sanitized_subject.replace("Re: ", "").replace("RE: ", "").strip()
        return (
            f"Yth. Pengirim,\n\n"
            f"Terima kasih atas email Anda terkait '{clean_subj}'. "
            f"Pesan Anda telah kami terima dan sedang dalam proses penanganan tim kami.\n\n"
            f"Kami akan segera menghubungi Anda kembali dengan informasi selengkapnya.\n\n"
            f"Salam hormat,\n"
            f"{context_loader.get_bot_identity()['name']}\n"
            f"{context_loader.get_bot_identity()['organization']}"
        )

    def classify_email(self, sender: str, subject: str, body: str) -> dict:
        """
        Classifies an email following the 5-step procedural workflow from SKILL.md.
        Returns a structured dictionary matching the JSON Schema contract.
        """
        # Redact PII before classification
        sanitized_body = privacy_enclave.redact_pii(body) if settings.ENCLAVE_PII_REDACTION else body
        sanitized_subj = privacy_enclave.redact_pii(subject) if settings.ENCLAVE_PII_REDACTION else subject

        if self._client:
            try:
                skill_context = context_loader.get_skill() or ""
                prompt = (
                    f"{skill_context}\n\n"
                    f"--- EMAIL INPUT ---\n"
                    f"Sender: {sender}\n"
                    f"Subject: {sanitized_subj}\n"
                    f"Body: {sanitized_body}\n\n"
                    f"Execute the 5-step procedural workflow and return ONLY valid JSON."
                )
                response = self._client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config={"system_instruction": self._system_prompt} if self._system_prompt else None
                )
                if response and response.text:
                    import json
                    return json.loads(response.text.strip())
            except Exception as e:
                logger.error(f"Email classification error: {e}")

        # Heuristic fallback classification
        category = "INFO_UPDATE"
        priority = "LOW"
        body_lower = sanitized_body.lower()
        subject_lower = sanitized_subj.lower()

        if any(w in body_lower for w in ("otp", "kode verifikasi", "verification code", "2fa", "pin")):
            category = "OTP_ALERT"
            priority = "CRITICAL"
        elif any(w in subject_lower for w in ("pesanan", "order", "buyer", "pembelian", "beli")):
            category = "BUYER_ORDER"
            priority = "HIGH"
        elif any(w in subject_lower for w in ("invoice", "tagihan", "faktur", "billing", "payment")):
            category = "INVOICE_BILLING"
            priority = "HIGH"
        elif any(w in subject_lower for w in ("undangan", "invitation", "approval", "persetujuan")):
            category = "INVITATION_APPROVAL"
            priority = "HIGH"
        elif any(w in body_lower for w in ("login", "reset password", "authentication")):
            category = "AUTH_LINK"
            priority = "HIGH"
        elif any(w in subject_lower for w in ("rapat", "meeting", "agenda", "jadwal")):
            category = "CALENDAR_INVITE"
            priority = "MEDIUM"
        elif any(w in subject_lower for w in ("vendor", "update vendor", "mitra", "supplier")):
            category = "VENDOR_UPDATE"
            priority = "MEDIUM"

        return {
            "email_metadata": {"sender": sender, "subject": subject, "received_at": ""},
            "classification": {"category": category, "priority": priority, "summary": f"[Heuristik] {subject}"},
            "action_payload": {"type": "TEXT_SUMMARY_ONLY", "buttons": []}
        }


ai_helper = AIHelper()
