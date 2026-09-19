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
import requests

logger = setup_logger("AI_HELPER")


class AIHelper:
    """Provides LLM-assisted features with Google GenAI & Mistral AI, plus graceful offline fallbacks."""

    def __init__(self):
        self._gemini_client = None
        self._mistral_api_key = settings.MISTRAL_API_KEY
        self._mistral_model = settings.MISTRAL_MODEL
        self._mistral_endpoint = settings.MISTRAL_ENDPOINT
        self._system_prompt: str = ""
        self._initialize_clients()
        self._load_system_context()

    def _initialize_clients(self):
        # 1. Initialize Mistral AI Client (Primary / MODE_MISTRAL)
        if self._mistral_api_key:
            logger.info(f"Mistral AI engine successfully connected (Model: {self._mistral_model}).")
        
        # 2. Initialize Google GenAI Client
        if settings.GEMINI_API_KEY:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
                logger.info("Google GenAI client successfully initialized.")
            except Exception as e:
                logger.warning(f"Failed to initialize GenAI client: {e}.")
                self._gemini_client = None
        else:
            logger.debug("GEMINI_API_KEY not configured.")

    def _call_mistral(self, prompt: str, system_inst: str = "") -> str:
        """Executes fast inference via Mistral AI REST endpoint."""
        if not self._mistral_api_key:
            return ""
        headers = {
            "Authorization": f"Bearer {self._mistral_api_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system_inst:
            messages.append({"role": "system", "content": system_inst})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self._mistral_model,
            "messages": messages,
            "temperature": 0.3
        }
        try:
            resp = requests.post(f"{self._mistral_endpoint}/chat/completions", headers=headers, json=payload, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            else:
                logger.warning(f"Mistral API returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"Error communicating with Mistral AI: {e}")
        return ""

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
        """Summarizes email or chat text concisely with automated PII redaction (Mistral AI + Gemini fallback)."""
        if not text or not text.strip():
            return "Tidak ada konten untuk diringkas."

        # Redact sensitive PII before any AI processing
        sanitized_text = privacy_enclave.redact_pii(text) if settings.ENCLAVE_PII_REDACTION else text

        prompt = (
            f"Ringkas teks berikut secara singkat, padat, dan profesional "
            f"dalam maksimal {max_words} kata menggunakan Bahasa Indonesia:\n\n{sanitized_text}"
        )

        # 1. Primary: Mistral AI (MODE_MISTRAL)
        if self._mistral_api_key:
            try:
                mistral_resp = self._call_mistral(prompt, self._system_prompt)
                if mistral_resp:
                    telemetry_hub.record_token_usage(
                        raw_prompt_tokens=int(len(prompt.split()) * 1.3),
                        compressed_prompt_tokens=int(len(prompt.split()) * 1.0),
                        completion_tokens=int(len(mistral_resp.split()) * 1.3),
                        tier="tier_1_subscription",
                        model=self._mistral_model
                    )
                    return mistral_resp
            except Exception as e:
                logger.warning(f"Mistral AI summarization failed: {e}. Falling back to Gemini/Heuristic.")

        # 2. Secondary: Google GenAI (Gemini)
        if self._gemini_client:
            try:
                response = self._gemini_client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config={"system_instruction": self._system_prompt} if self._system_prompt else None
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                logger.error(f"GenAI summarization error: {e}. Using deterministic fallback.")

        # 3. Deterministic heuristic fallback
        words = sanitized_text.split()
        if len(words) <= max_words:
            return sanitized_text
        return " ".join(words[:max_words]) + "..."

    def draft_reply(self, subject: str, body: str, tone: str = "profesional, sopan, dan solutif") -> str:
        """Drafts an intelligent email reply with PII redaction protection (Mistral AI + Gemini fallback)."""
        # Redact sensitive PII
        sanitized_subject = privacy_enclave.redact_pii(subject) if settings.ENCLAVE_PII_REDACTION else subject
        sanitized_body = privacy_enclave.redact_pii(body) if settings.ENCLAVE_PII_REDACTION else body

        prompt = (
            f"Buatkan draf balasan email dengan nada {tone}.\n\n"
            f"Subjek Asli: {sanitized_subject}\n"
            f"Isi Pesan Asli:\n{sanitized_body}\n\n"
            f"Tulis balasan langsung tanpa pembuka meta (misal: 'Berikut adalah draf...')."
        )

        # 1. Primary: Mistral AI (MODE_MISTRAL)
        if self._mistral_api_key:
            try:
                mistral_resp = self._call_mistral(prompt, self._system_prompt)
                if mistral_resp:
                    return mistral_resp
            except Exception as e:
                logger.warning(f"Mistral AI draft generation failed: {e}. Falling back to Gemini/Heuristic.")

        # 2. Secondary: Google GenAI (Gemini)
        if self._gemini_client:
            try:
                response = self._gemini_client.models.generate_content(
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
