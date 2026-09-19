---
name: vendor-invoice-reconciliation
description: Automatically synthesized procedural rule for finance workflow
version: 1.0.0
standard: agentskills.io/v1
created_at: "2026-09-19 18:00:39"
turns_analyzed: 5
---

# 📜 Skill: vendor-invoice-reconciliation

> **Domain**: `finance` | **Extracted via**: Hermes Skill Creation Loop (Pillar 1)

## 📋 Procedural Execution Workflow
1. **User Step**: Permintaan rekonsiliasi faktur vendor B2B
2. **Assistant Step**: Ambil data lampiran invoice dari Gmail
3. **Agent Step**: Ekstrak nomor invoice dan total nominal tagihan
4. **Agent Step**: Verifikasi NIK dan data rekening dengan Privacy Enclave
5. **Assistant Step**: Kirim draf balasan konfirmasi ke Telegram Admin

## 🛡️ Guardrails & Operational Constraints
- Verify inputs before triggering actions.
- Enforce latency ACK SLA <150ms.
- Maintain PII Redaction for sensitive identifiers.
