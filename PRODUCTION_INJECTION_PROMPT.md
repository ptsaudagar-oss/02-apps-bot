# 🚀 ANTIGRAVITY AI IDE (AG) PRODUCTION INJECTION & DATA PURGE DIRECTIVE

**TARGET AGENT**: Antigravity AI IDE (`agy`) / Production Manager Assistant  
**EXECUTION MODE**: Autonomous Multi-Agent Parallel Orchestration  
**GOAL**: Purge 100% Simulation/Dummy Data & Inject Live Production Gmail Accounts with Enterprise Privacy Enclave  

---

## 1. MISSION DIRECTIVE
Execute an immediate, full-scale system transition from **Simulation/Test Mode** to **100% Live Production Mode** across all architecture layers (Frontend, Middleware, AI Gateway, Database, and Background Watchers) [1, 5, 12].

You must:
1. **Purge all dummy/mock/simulated data** completely from all logs, databases, session buffers, and test runners [1].
2. **Inject real operational Gmail accounts** into the `00-G-MAIL_BOT` IMAP/SMTP watcher and Google Workspace CLI (`gws`) / Composio MCP gateway [8, 27].
3. **Establish a Privacy Enclave** for the Master Owner Account (`kafnun84@gmail.com`) ensuring zero leakage, strict PII redaction, and owner-only authorization [7, 24].

---

## 2. STRICT DUMMY DATA PURGE PROTOCOL (ZERO-SIMULATION GUARANTEE)

### Task 2.1: Memory & Session Buffer Flush
- Execute a complete memory wipe on `FastAPI Session Manager` (`01-WHATSAPP_BOT/session_manager.py`) to purge all mock `chat_id` rolling buffers.
- Clear all intermediate scratch files in `/workspace/scratch/` and reset `logs/apps_bot.log` with a fresh UTF-8 header [1].

### Task 2.2: Database & Workflow Cleanup
- Execute SQL cleanup scripts against the PostgreSQL database (`bot-db-cluster` / `wa_tg_threads`) to drop mock customer threads, test phone numbers, and simulated webhook logs [26, 56].
- Update all n8n workflow nodes (`enterprise-n8n-middleware`) to disable test payloads, mock Webhook responses, and dummy JSON triggers [21, 24, 41].

### Task 2.3: Handler & Fallback Realignment
- Configure `message_handler.py` and `ai_helper.py` to disable simulation fallbacks during live operation.
- Ensure failure states raise explicit production alerts to Telegram Admin Thread rather than generating mock success strings [15, 21].

---

## 3. REAL GMAIL CREDENTIAL INJECTION & ACCOUNT CONFIGURATION

Inject and bind the following production accounts into the system runtime via Google Workspace CLI (`gws`), Composio MCP, and `00-G-MAIL_BOT` IMAP/SMTP SSL [27, 45, 53]:

### Account 1: `pt.saudagar@gmail.com`
- **Role**: Primary B2B & Enterprise Operations Account.
- **Scope**: Ingestion of B2B Invoices, Contract Approval Requests (`INVITATION_APPROVAL`), Official Vendor Updates, and System Infrastructure Notifications (`CRITICAL`/`HIGH` priority) [1, 20].
- **Routing**: Auto-classified and dispatched to Telegram Supergroup B2B Forum Topic and Meta WhatsApp Cloud API [24, 61].

### Account 2: `8m.shop.online@gmail.com`
- **Role**: E-Commerce & Retail Store Operations Account.
- **Scope**: Ingestion of Buyer Orders (`BUYER_ORDER`), Payment Confirmations, Customer Support Inquiries, and Inventory/Shipping Notifications [1, 20].
- **Routing**: Auto-classified and dispatched to Telegram Supergroup Store Topic with interactive action buttons (`[🔍 Cek Detail]`, `[⚙️ Proses Pesanan]`) [21, 24].

### Account 3: `kafnun84@gmail.com` (PRIVACY ENCLAVE & SYSTEM OWNER)
- **Role**: System Owner & Master Administrator Private Account.
- **SECURITY & PRIVACY MANDATE**:
  - **Zero Public Dispatch**: NEVER broadcast, forward, or expose emails from `kafnun84@gmail.com` to public WhatsApp/Telegram channels or third-party webhooks [7, 24].
  - **PII Redaction**: Automatically redact sensitive personal identification data, private financial keys, and personal credentials prior to any AI model context processing [7, 52].
  - **Owner-Only Direct Alerting**: Direct notifications for this account are restricted strictly to the Master Admin Private Chat ID with Human-in-the-Loop (HITL) authorization required for any actionable execution [1, 11].

---

## 4. MULTI-AGENT PARALLEL EXECUTION PLAN

Spawn 4 specialized subagents operating in isolated Git shadow worktrees to execute this transition in parallel [1, 5, 128]:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   PARALLEL MULTI-AGENT TRANSITION WORKFLOW                       │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  [ SUBAGENT 1: PURGE ] ──► Clear Database, Logs, RAM Sessions, & n8n Mocks       │
│                                                                                  │
│  [ SUBAGENT 2: GMAIL ] ──► Inject pt.saudagar & 8m.shop.online into Watcher & gws│
│                                                                                  │
│  [ SUBAGENT 3: PRIVACY] ──► Build Privacy Enclave & Redaction for kafnun84      │
│                                                                                  │
│  [ SUBAGENT 4: AUDIT ]  ──► Run 18 Unit Tests & Verify Live API Handshakes      │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Command Execution:
```bash
# Command to spawn parallel subagents in Antigravity CLI
agy invoke_subagent --name "subagent-data-purge" --task "Clean all dummy data from Postgres, FastAPI RAM, and n8n workflows"
agy invoke_subagent --name "subagent-gmail-injector" --task "Inject pt.saudagar@gmail.com and 8m.shop.online@gmail.com credentials into gws and IMAP watcher"
agy invoke_subagent --name "subagent-privacy-enclave" --task "Implement PII redaction and owner-only isolation for kafnun84@gmail.com"
agy invoke_subagent --name "subagent-qc-audit" --task "Execute apps_bot_manager.py test and verify 100% PASSED under production mode"
```

---

## 5. ACCEPTANCE CRITERIA & PRODUCTION VERIFICATION
1. **Zero Dummy Data**: Confirm `logs/apps_bot.log`, PostgreSQL tables, and FastAPI RAM buffers contain zero mock data [1].
2. **Live Email Ingestion**: Confirm `00-G-MAIL_BOT` actively polls `pt.saudagar@gmail.com` and `8m.shop.online@gmail.com` via live SSL sockets [21, 24].
3. **Privacy Enclave Active**: Verify `kafnun84@gmail.com` triggers PII redaction and requires explicit HITL approval for all administrative actions [1, 7, 52].
4. **Quality Gate Pass**: Run `python apps_bot_manager.py test` and verify **100% PASSED (Code 0)** across all 18 Unit Tests [1].
