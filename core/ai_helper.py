"""
AI Helper Module for APPS_BOT.
Integrates Google GenAI (Gemini) for text summarization, auto-drafting, and intent classification.
Includes deterministic heuristic fallback if API key is not configured.
"""

from typing import Optional
from core.config import settings
from core.logger import setup_logger

logger = setup_logger("AI_HELPER")


class AIHelper:
    """Provides LLM-assisted features with graceful offline fallbacks."""

    def __init__(self):
        self._client = None
        self._initialize_client()

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

    def summarize_text(self, text: str, max_words: int = 100) -> str:
        """Summarizes email or chat text concisely."""
        if not text or not text.strip():
            return "Tidak ada konten untuk diringkas."

        if self._client:
            try:
                prompt = (
                    f"Ringkas teks berikut secara singkat, padat, dan profesional "
                    f"dalam maksimal {max_words} kata menggunakan Bahasa Indonesia:\n\n{text}"
                )
                response = self._client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                logger.error(f"GenAI summarization error: {e}. Using heuristic fallback.")

        # Heuristic fallback (Clean extraction of first key sentences)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        preview = " ".join(lines[:3])
        words = preview.split()
        if len(words) > max_words:
            preview = " ".join(words[:max_words]) + "..."
        return f"[Ringkasan Cepat]: {preview}"

    def draft_reply(self, subject: str, body: str, tone: str = "professional") -> str:
        """Generates a contextual reply draft for an email or inquiry."""
        if self._client:
            try:
                prompt = (
                    f"Buat draf balasan pesan dengan nada {tone} dalam Bahasa Indonesia untuk:\n"
                    f"Subjek: {subject}\n"
                    f"Isi: {body}\n\n"
                    f"Format: Langsung berikan teks draf balasan siap kirim."
                )
                response = self._client.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                logger.error(f"GenAI draft generation error: {e}")

        # Fallback template
        return (
            f"Halo, terima kasih atas pesan Anda mengenai '{subject}'. "
            f"Pesan Anda telah kami terima dan saat ini sedang ditinjau. "
            f"Kami akan segera menindaklanjutinya. Salam hormat."
        )


ai_helper = AIHelper()
