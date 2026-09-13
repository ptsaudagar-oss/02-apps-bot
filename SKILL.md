# SKILL.md — Procedural Skill Specification

Skill Name: `email_classification_and_action_handler`  
Engine Compatibility: Hermes Agent / Gemini 3.6 Flash / 9Router Proxy  
Target Framework: APPS_BOT Layer 2 (Telegram Gmail Bot) & Layer 3 (WhatsApp Bot)  

---

## 🎯 1. Overview & Core Objective

Skill ini menyediakan panduan langkah demi langkah (*procedural reasoning*) bagi Hermes Agent untuk mengekstrak, mengklasifikasikan, memprioritaskan, dan menghasilkan **JSON Schema Action Payload** dari email Gmail yang bervariasi dan kompleks secara otomatis.

---

## 📥 2. Input Specification

Skill ini menerima input berupa objek JSON metadata email dari *Gmail Push Watcher*:

```json
{
  "sender": "string (email address / display name)",
  "subject": "string",
  "body_plain": "string (raw body text)",
  "received_at": "ISO-8601 timestamp"
}
```

---

## ⚙️ 3. Step-by-Step Procedural Workflow

When triggered, Hermes Agent MUST execute the following 5 reasoning steps:

```text
[Step 1: Sanitize & Inspect] ➔ [Step 2: Intent & Category Mining] ➔ 
[Step 3: Priority Scoring] ➔ [Step 4: Action Payload Generation] ➔ 
[Step 5: Output JSON Validation]
```

### Step 1: Sanitize & Inspect
1. Strip HTML tags and excess whitespace from `body_plain`.
2. Extract key entities: sender domain, verification codes, date/time references, links, and financial amounts.

### Step 2: Intent & Category Mining
Classify the intent into exactly ONE of the following primary categories:
* `OTP_ALERT`: Contains OTP, 2FA, PIN, or verification codes.
* `INVITATION_APPROVAL`: Requires decision/approval for invitation, budget, or request.
* `AUTH_LINK`: Contains login link, authentication URL, or password reset link.
* `CALENDAR_INVITE`: Specific scheduled event with time and date.
* `PURCHASE_ORDER`: Incoming customer order, invoice, or purchase receipt.
* `INFO_UPDATE`: Informational newsletter, update, system report, or general FYI.

### Step 3: Priority Scoring
Assign priority tier based on category:
* `CRITICAL`: `OTP_ALERT` (Process immediately < 5s).
* `HIGH`: `INVITATION_APPROVAL`, `AUTH_LINK`, `PURCHASE_ORDER`.
* `MEDIUM`: `CALENDAR_INVITE`.
* `LOW`: `INFO_UPDATE` (Consolidate into keypoint summary).

### Step 4: Action Payload Generation
Construct the `action_payload` object based on category:
* For `OTP_ALERT`: Extract code as plain text highlight.
* For `INVITATION_APPROVAL`: Create interactive buttons `[ ✅ Setujui, ❌ Tolak ]`.
* For `AUTH_LINK`: Create quick action buttons `[ 🔗 Approve Link, ❌ Decline ]`.
* For `CALENDAR_INVITE`: Generate `[ 📅 Add to Google Calendar ]` action link/payload.
* For `PURCHASE_ORDER`: Create buttons `[ 📦 Proses Pesanan, ❌ Decline ]`.
* For `INFO_UPDATE`: Summarize body into 3 bullet points.

---

## 📋 4. Output JSON Schema Specification

Hermes Agent MUST respond ONLY with a valid JSON object matching this schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "email_metadata": {
      "type": "object",
      "properties": {
        "sender": { "type": "string" },
        "subject": { "type": "string" },
        "received_at": { "type": "string" }
      },
      "required": ["sender", "subject", "received_at"]
    },
    "classification": {
      "type": "object",
      "properties": {
        "category": { 
          "type": "string",
          "enum": ["OTP_ALERT", "INVITATION_APPROVAL", "AUTH_LINK", "CALENDAR_INVITE", "PURCHASE_ORDER", "INFO_UPDATE"]
        },
        "priority": {
          "type": "string",
          "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        },
        "summary": { "type": "string" }
      },
      "required": ["category", "priority", "summary"]
    },
    "action_payload": {
      "type": "object",
      "properties": {
        "type": {
          "type": "string",
          "enum": ["PLAIN_TEXT_HIGHLIGHT", "INTERACTIVE_BUTTONS", "CALENDAR_EVENT", "TEXT_SUMMARY_ONLY"]
        },
        "extracted_data": { "type": "object" },
        "buttons": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "label": { "type": "string" },
              "action_id": { "type": "string" }
            },
            "required": ["label", "action_id"]
          }
        }
      },
      "required": ["type", "buttons"]
    }
  },
  "required": ["email_metadata", "classification", "action_payload"]
}
```

---

## 🛠️ 5. Error Handling & Failover

1. **Unclassifiable Email**: Default category to `INFO_UPDATE`, priority `LOW`, type `TEXT_SUMMARY_ONLY`.
2. **Missing Time/Date in Event**: Omit `CALENDAR_EVENT` action and fallback to `INTERACTIVE_BUTTONS` asking user to specify time.
3. **Dispatch Failure**: If n8n or Meta API returns error, log to `logs/apps_bot.log` and trigger `Dual Dispatcher` failover to Local Gateway.
