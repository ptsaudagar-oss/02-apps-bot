# MEMORY.md — Persistent Long-Term Memory Store

System: APPS_BOT Multi-Channel Autonomous AI System  
Agent Framework: Hermes Agent Engine  
Last Updated: 2026-09-13  

---

## 👤 1. User & Role Context
* **Production Manager Persona**: User is a Software & Ecosystem Production Manager managing the `02-APPS_BOT` ecosystem.
* **Communication Channels**:
  * Primary VIP Channel: Telegram Supergroup / Direct Chat.
  * Primary Public Channel: WhatsApp Cloud API / Local Gateway Bridge.
* **Language & Communication Preference**: Indonesian language, clear, empathetic, and consistently using the **"Restoran Modern Berbintang"** analogy for architecture concepts.

---

## 🏛️ 2. Core System Policies & Architectural Rules

### A. WhatsApp Dual Dispatcher & Failover Policy
1. **Primary Route**: Always attempt dispatch via Meta WhatsApp Cloud API (`WHATSAPP_PROVIDER_PRIMARY=meta`).
2. **Secondary Route (Failover)**: If Meta API returns HTTP != 200, Token Expired (401), or Server Error (500), automatically failover to Local Gateway Bridge (`http://127.0.0.1:3000/api/send`).
3. **Safety Fallback**: If both Meta and Local Gateway are unreachable, log the payload to safe simulation log (`logs/apps_bot.log`) without crashing the application (*Zero-Crash Guarantee*).

### B. Gmail Push Watcher & Security
1. **Authentication**: Use Google App Password via IMAP/SMTP SSL (`GMAIL_AUTH_MODE=app_password`) to prevent token expiration issues.
2. **Watcher Schedule**: Proactive Push Watcher runs every 60 seconds (or configurable 5–10 minutes) to poll unread emails.

### C. AI Proxy & Token Optimization (9Router)
1. **Endpoint Target**: All LLM reasoning requests pass through local 9Router proxy at `http://localhost:20128/v1` (OpenAI-compatible).
2. **Fallback Strategy**: 
   * Tier 1: Primary Subscriptions / OAuth (Claude, Codex, Gemini 3.6 Flash).
   * Tier 2: Commercial APIs (DeepSeek, GLM, MiniMax).
   * Tier 3: Free Tiers / Credits.
3. **Token Saver**: RTK Token Compression active for tool results (20%–40% token savings).

---

## 📥 3. Learned Email Categorization & Action Patterns

Hermes Agent maintains persistent rules for dynamic email processing:

| Category ID | Trigger Keywords / Intent | Classification | Required Action Payload | Target Channel |
| :--- | :--- | :--- | :--- | :--- |
| `OTP_ALERT` | Verification code, OTP, 2FA, Security Code | `CRITICAL` | Extract code text, instant notification | WhatsApp + Telegram |
| `INVITATION_APPROVAL` | Invitation, Approval Required, Confirmation | `HIGH` | Interactive Buttons (`Approve` / `Decline`) | Telegram / WhatsApp |
| `AUTH_LINK` | Magic Link, Password Reset, Authenticate | `HIGH` | Quick Action Buttons (`Approve Link` / `Decline`) | WhatsApp / Telegram |
| `CALENDAR_INVITE` | Event Invitation, Meeting Schedule, Webinar | `MEDIUM` | `Add to Google Calendar` / `Local Cal` Action | WhatsApp / Telegram |
| `PURCHASE_ORDER` | New Order, Buyer Receipt, Invoice, Payment | `HIGH` | Interactive Order Check (`Process` / `Decline`) | WhatsApp + Telegram |
| `INFO_UPDATE` | Newsletter, Maintenance, Policy Update, FYI | `LOW` | Keypoint Summary (Markdown Bullet Points) | Telegram (Batch/Daily) |

---

## 🧪 4. System Health & Quality Control History
* **Test Suite**: `python apps_bot_manager.py test` (18 Unit Tests across Layer 1 Core, Layer 2 Telegram, Layer 3 WhatsApp).
* **Last Verified Status**: **100% PASSED (Code 0)**.
* **Log Rotation Standard**: `logs/apps_bot.log` max size 10MB with UTF-8 encoding.
