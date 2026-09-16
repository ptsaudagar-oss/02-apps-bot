"""
Context Loader Module for APPS_BOT.
Reads and caches the foundational context documents (MEMORY.md, SOUL.md, USER.md, USER-v2.md, ANTIGRAVITY_PARALLEL_ORCHESTRATION.md)
and exposes structured accessors for system prompts, architecture context, user profile, and parallel orchestration.

Source Directives:
  - SOUL.md §1: Core Identity → Persona for AI system prompt
  - SOUL.md §2: F.O.R.G.E. Methodology → Operational reasoning framework
  - SOUL.md §4: Security & Governance → Guardrails
  - USER.md §2: Communication & Workflow Preferences → Tone & style
  - MEMORY.md §1-3: Active Architecture → Environment facts
  - ANTIGRAVITY_PARALLEL_ORCHESTRATION.md §1-5: Multi-Agent Parallel Orchestration Directives
"""

import os
from typing import Optional, Dict
from core.config import ROOT_DIR
from core.logger import setup_logger

logger = setup_logger("CONTEXT_LOADER")

# Paths to context documents (relative to project root)
CONTEXT_FILES = {
    "MEMORY": os.path.join(ROOT_DIR, "MEMORY.md"),
    "SOUL": os.path.join(ROOT_DIR, "SOUL.md"),
    "USER": os.path.join(ROOT_DIR, "USER.md"),
    "USER_V2": os.path.join(ROOT_DIR, "USER-v2.md"),
    "SKILL": os.path.join(ROOT_DIR, "SKILL.md"),
    "ORCHESTRATION": os.path.join(ROOT_DIR, "ANTIGRAVITY_PARALLEL_ORCHESTRATION.md"),
    "ORCHESTRATION_V2": os.path.join(ROOT_DIR, "ANTIGRAVITY_PARALLEL_ORCHESTRATION-v2.md"),
}

# In-memory cache
_cache: Dict[str, Optional[str]] = {}


def _load_file(key: str) -> Optional[str]:
    """Loads a context file from disk with caching."""
    if key in _cache:
        return _cache[key]

    filepath = CONTEXT_FILES.get(key)
    if not filepath or not os.path.exists(filepath):
        logger.debug(f"Context file '{key}' not found at: {filepath}")
        _cache[key] = None
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
        _cache[key] = content
        logger.info(f"Context document '{key}' loaded successfully ({len(content)} chars).")
        return content
    except Exception as e:
        logger.error(f"Failed to load context file '{key}': {e}")
        _cache[key] = None
        return None


def get_soul() -> Optional[str]:
    """Returns SOUL.md content (Persona, Guardrails, Core Directives)."""
    return _load_file("SOUL")


def get_memory() -> Optional[str]:
    """Returns MEMORY.md content (Architecture Map, Endpoints, Cloud State)."""
    return _load_file("MEMORY")


def get_user_profile() -> Optional[str]:
    """Returns USER-v2.md content (preferred), falls back to USER.md."""
    content = _load_file("USER_V2")
    if content:
        return content
    return _load_file("USER")


def get_skill() -> Optional[str]:
    """Returns SKILL.md content (Email Classification Procedural Workflow)."""
    return _load_file("SKILL")


def get_orchestration() -> Optional[str]:
    """Returns ANTIGRAVITY_PARALLEL_ORCHESTRATION.md content (Parallel Multi-Agent Architecture & Directives)."""
    content = _load_file("ORCHESTRATION")
    if content:
        return content
    return _load_file("ORCHESTRATION_V2")


def get_system_prompt() -> str:
    """
    Builds the unified AI system prompt by combining SOUL.md + USER.md directives.
    This is injected into Gemini/9Router as the `system_instruction` parameter.
    
    Structure:
      1. SOUL §1: Core Identity & Role
      2. SOUL §2: F.O.R.G.E. Methodology
      3. SOUL §4: Security Boundaries
      4. USER §2: Communication Preferences
    """
    parts = []

    soul = get_soul()
    if soul:
        parts.append("=== SYSTEM PERSONA & DIRECTIVES ===")
        parts.append(soul)

    user = get_user_profile()
    if user:
        parts.append("\n=== USER PROFILE & COMMUNICATION STANDARDS ===")
        parts.append(user)

    if not parts:
        return (
            "You are Antigravity Assistant Production Manager (APM), "
            "an autonomous system orchestrator for multi-channel messaging systems. "
            "Respond in Bahasa Indonesia, professionally and concisely."
        )

    return "\n\n".join(parts)


def get_architecture_context() -> str:
    """
    Returns a formatted architecture summary from MEMORY.md for diagnostic displays.
    Falls back to a static summary if MEMORY.md is unavailable.
    """
    memory = get_memory()
    if memory:
        return memory

    return (
        "### Architecture Context (Static Fallback)\n"
        "- 9Router AI Gateway: http://localhost:20128/v1\n"
        "- FastAPI Web Server: http://127.0.0.1:8080\n"
        "- Gmail Watcher: IMAP/SMTP SSL Daemon\n"
        "- Render Cloud IaC: render.yaml (4 services)\n"
        "- Git Repository: ptsaudagar-oss/02-apps-bot"
    )


def get_bot_identity() -> Dict[str, str]:
    """
    Extracts structured bot identity from SOUL.md §1 and USER.md §1.
    Returns a dictionary with key identity fields.
    """
    return {
        "name": "Antigravity Assistant Production Manager (APM)",
        "role": "Autonomous System Orchestrator & Ecosystem Lead",
        "engine": "Hermes Agent Cognitive Kernel + Antigravity AI CLI",
        "owner": "Kafnun Asep Nurhuda Al-Hakim",
        "organization": "PT. Saudagar",
        "email": "pt.saudagar@gmail.com",
        "methodology": "F.O.R.G.E. (Foundation → Outline → Rock'n'Roll → Guard → Evolve)",
    }


def get_all_context_summary() -> str:
    """Returns a formatted summary of all loaded context documents for CLI display."""
    lines = []
    for key, filepath in CONTEXT_FILES.items():
        exists = os.path.exists(filepath)
        content = _load_file(key)
        size = f"{len(content)} chars" if content else "N/A"
        status = "✅ LOADED" if content else ("⚠️ EMPTY" if exists else "❌ NOT FOUND")
        lines.append(f"  • {key:12s} : {status} ({size}) → {os.path.basename(filepath)}")
    return "\n".join(lines)


def reload_all() -> None:
    """Clears cache and reloads all context documents from disk."""
    _cache.clear()
    for key in CONTEXT_FILES:
        _load_file(key)
    logger.info("All context documents reloaded from disk.")
