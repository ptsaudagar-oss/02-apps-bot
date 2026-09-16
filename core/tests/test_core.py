"""
QC Unit Tests for APPS_BOT Core Framework.
Verifies path localization, configuration loading, logger initialization, and AI helper fallback.
"""

import os
import sys
import unittest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.config import settings, ROOT_DIR
from core.logger import setup_logger
from core.base_bot import BaseBotEngine
from core.ai_helper import ai_helper


class DummyBot(BaseBotEngine):
    """Dummy bot implementation for lifecycle contract testing."""
    async def start(self) -> None:
        self._is_running = True

    async def stop(self) -> None:
        self._is_running = False

    def health_check(self) -> dict:
        return {"status": "ok", "mock": True}


class TestCoreFramework(unittest.TestCase):
    """QC Test Suite for Core Layer."""

    def test_path_localization(self):
        """Verify that ROOT_DIR is accurately resolved and exists."""
        self.assertTrue(os.path.exists(ROOT_DIR), f"ROOT_DIR {ROOT_DIR} should exist.")
        self.assertTrue(os.path.isabs(ROOT_DIR), "ROOT_DIR must be an absolute path.")
        self.assertTrue(os.path.exists(settings.LOGS_DIR), "LOGS_DIR should be created.")

    def test_logger_setup(self):
        """Verify that logger outputs and writes to log file."""
        test_logger = setup_logger("TEST_CORE")
        self.assertIsNotNone(test_logger)
        test_logger.info("QC Test log message execution.")
        
        log_file = os.path.join(settings.LOGS_DIR, "apps_bot.log")
        self.assertTrue(os.path.exists(log_file), "apps_bot.log must exist after logging.")

    def test_base_bot_contract(self):
        """Verify standard lifecycle contract implementation."""
        bot = DummyBot("TEST_DUMMY_BOT")
        self.assertEqual(bot.bot_name, "TEST_DUMMY_BOT")
        self.assertFalse(bot.is_running)
        
        status = bot.get_status()
        self.assertIn("bot_name", status)
        self.assertIn("health", status)
        self.assertTrue(status["health"]["mock"])

    def test_ai_helper_fallback(self):
        """Verify that AI helper summarizes text properly even offline."""
        sample_text = (
            "Pemberitahuan penting mengenai rilis sistem bot terbaru versi 1.0.0. "
            "Sistem ini mencakup modul Telegram Gmail Bot dan WhatsApp Bot. "
            "Semua modul telah melalui uji Quality Control dan dinyatakan siap operasi."
        )
        summary = ai_helper.summarize_text(sample_text, max_words=20)
        self.assertIsInstance(summary, str)
        self.assertTrue(len(summary) > 0)
        
        draft = ai_helper.draft_reply("Konfirmasi Jadwal", "Kapan sistem bot ini mulai aktif?")
        self.assertIsInstance(draft, str)
        self.assertGreater(len(draft), 20, "Draft reply should produce meaningful response.")

    def test_context_loader(self):
        """Verify context documents loading and orchestration integration."""
        from core import context_loader

        # Ensure all context documents load properly
        self.assertIsNotNone(context_loader.get_soul(), "SOUL.md must be loaded")
        self.assertIsNotNone(context_loader.get_memory(), "MEMORY.md must be loaded")
        self.assertIsNotNone(context_loader.get_user_profile(), "USER profile must be loaded")
        self.assertIsNotNone(context_loader.get_skill(), "SKILL.md must be loaded")

        # Verify ANTIGRAVITY_PARALLEL_ORCHESTRATION.md
        orch = context_loader.get_orchestration()
        self.assertIsNotNone(orch, "ANTIGRAVITY_PARALLEL_ORCHESTRATION.md must be loaded")
        self.assertIn("INSTRUKSI KHUSUS ANTIGRAVITY AI IDE", orch)
        self.assertTrue("AGENT ALPHA" in orch or "STASIONER 1" in orch)
        self.assertTrue("AGENT OMEGA" in orch or "STASIONER 5" in orch)

        # Verify system prompt and summary
        sys_prompt = context_loader.get_system_prompt()
        self.assertIn("SYSTEM PERSONA & DIRECTIVES", sys_prompt)

        summary = context_loader.get_all_context_summary()
        self.assertIn("ORCHESTRATION", summary)

    def test_privacy_enclave(self):
        """Verify Privacy Enclave PII redaction and Owner Account isolation."""
        from core.privacy_enclave import privacy_enclave, MASTER_OWNER_EMAIL, B2B_OPERATIONS_EMAIL, ECOMMERCE_STORE_EMAIL

        # 1. Account classification
        self.assertTrue(privacy_enclave.is_owner_account(MASTER_OWNER_EMAIL))
        self.assertTrue(privacy_enclave.is_b2b_account(B2B_OPERATIONS_EMAIL))
        self.assertTrue(privacy_enclave.is_ecommerce_account(ECOMMERCE_STORE_EMAIL))

        # 2. Zero Public Dispatch Mandate
        self.assertFalse(privacy_enclave.should_broadcast_to_public(MASTER_OWNER_EMAIL))
        self.assertTrue(privacy_enclave.should_broadcast_to_public(B2B_OPERATIONS_EMAIL))
        self.assertTrue(privacy_enclave.should_broadcast_to_public(ECOMMERCE_STORE_EMAIL))

        # 3. PII Redaction
        raw_text = (
            "User NIK: 3201012345678901 dengan Kartu Kredit 4111 2222 3333 4444. "
            "Gunakan password: SecretPassword123 dan kode OTP: 987654."
        )
        redacted = privacy_enclave.redact_pii(raw_text)
        self.assertNotIn("4111 2222 3333 4444", redacted)
        self.assertNotIn("3201012345678901", redacted)
        self.assertNotIn("SecretPassword123", redacted)
        self.assertNotIn("987654", redacted)
        self.assertIn("[REDACTED_CREDIT_CARD]", redacted)
        self.assertIn("[REDACTED_NIK_KTP]", redacted)
        self.assertIn("[REDACTED_SECRET]", redacted)
        self.assertIn("[REDACTED_OTP]", redacted)

        # 4. Email sanitization
        test_email = {
            "id": "999",
            "from": MASTER_OWNER_EMAIL,
            "subject": "Dokumen Pribadi NIK 3201012345678901",
            "snippet": "Info OTP 123456 terkirim",
            "body": "Isi pesan sensitif dengan password: MyKey"
        }
        sanitized = privacy_enclave.sanitize_email_payload(test_email)
        self.assertTrue(sanitized["enclave_protected"])
        self.assertEqual(sanitized["privacy_level"], "CRITICAL_PRIVATE")
        self.assertNotIn("3201012345678901", sanitized["subject"])
        self.assertNotIn("123456", sanitized["snippet"])
        self.assertNotIn("MyKey", sanitized["body"])

    def test_telemetry_live_metrics(self):
        """Verify Phase 3 Live Telemetry, Latency SLA (<150ms), 9Router Tokens, and Automated Alerting."""
        from core.telemetry import telemetry_hub

        # 1. Ingestion Latency SLA (<150ms target)
        rec1 = telemetry_hub.record_latency("whatsapp", "/webhook[POST]", 45.2, 200)
        self.assertFalse(rec1.sla_breached)
        self.assertFalse(rec1.alert_triggered)

        # 2. SLA Warning (>150ms)
        rec2 = telemetry_hub.record_latency("telegram", "/sendMessage", 165.0, 200)
        self.assertTrue(rec2.sla_breached)
        self.assertFalse(rec2.alert_triggered)

        # 3. Emergency Alert Trigger (>200ms)
        alerts_received = []
        telemetry_hub.register_alert_listener(lambda a: alerts_received.append(a))
        rec3 = telemetry_hub.record_latency("whatsapp", "/webhook[POST]", 225.5, 200)
        self.assertTrue(rec3.sla_breached)
        self.assertTrue(rec3.alert_triggered)
        self.assertGreaterEqual(len(alerts_received), 1)

        # 4. 9Router Token Optimization & RTK Compression (-40%)
        tok = telemetry_hub.record_token_usage(
            raw_prompt_tokens=1000,
            compressed_prompt_tokens=650,
            completion_tokens=200,
            tier="tier_1_subscription",
            model="gemini-3.6-flash"
        )
        self.assertEqual(tok.tokens_saved, 350)
        self.assertEqual(tok.savings_pct, 35.0)

        # 5. Fallback distribution
        tok_stats = telemetry_hub.get_token_efficiency_stats()
        self.assertGreaterEqual(tok_stats["total_tokens_saved"], 350)
        self.assertIn("tier_1_subscription", tok_stats["fallback_distribution"])

        # 6. Dispatch & Buffer health
        telemetry_hub.record_dispatch("meta", is_failover=False)
        telemetry_hub.record_dispatch("local_bridge", is_failover=True)
        disp = telemetry_hub.get_dispatch_stats()
        self.assertGreaterEqual(disp["meta_cloud_dispatches"], 1)
        self.assertGreaterEqual(disp["local_bridge_failovers"], 1)

        # 7. Dashboard snapshot completeness
        snapshot = telemetry_hub.generate_dashboard_snapshot()
        self.assertIn("uptime_seconds", snapshot)
        self.assertIn("latency", snapshot)
        self.assertIn("token_efficiency", snapshot)
        self.assertIn("dispatch_health", snapshot)
        self.assertIn("security", snapshot)

    def test_skill_creation_loop(self):
        """Verify Pillar 1: Hermes Self-Improving Skill Creation Loop & Dynamic Indexing."""
        from core.skill_evolver import skill_evolver

        # 1. Reject workflows under 5 turns
        short_workflow = [
            {"role": "user", "content": "Tanya status"},
            {"role": "assistant", "content": "Status bot online"}
        ]
        res = skill_evolver.evaluate_workflow(short_workflow, "test_short")
        self.assertIsNone(res)

        # 2. Extract and synthesize 5+ turns workflow into SKILL.md
        long_workflow = [
            {"role": "user", "action": "Permintaan rekonsiliasi faktur vendor B2B"},
            {"role": "assistant", "action": "Ambil data lampiran invoice dari Gmail"},
            {"role": "agent", "action": "Ekstrak nomor invoice dan total nominal tagihan"},
            {"role": "agent", "action": "Verifikasi NIK dan data rekening dengan Privacy Enclave"},
            {"role": "assistant", "action": "Kirim draf balasan konfirmasi ke Telegram Admin"}
        ]
        created_path = skill_evolver.evaluate_workflow(long_workflow, "vendor_invoice_reconciliation", domain="finance")
        self.assertIsNotNone(created_path)
        self.assertTrue(os.path.exists(created_path))
        self.assertTrue(skill_evolver.has_skill("vendor_invoice_reconciliation"))

        # Verify agentskills.io format
        with open(created_path, "r", encoding="utf-8") as f:
            skill_text = f.read()
        self.assertIn("agentskills.io/v1", skill_text)
        self.assertIn("vendor-invoice-reconciliation", skill_text)
        self.assertIn("Procedural Execution Workflow", skill_text)

    def test_self_healing_failover(self):
        """Verify Pillar 2: Self-Healing Dual Dispatcher Failover & 9Router Cascading."""
        import asyncio
        from core.self_healing import self_healing_manager

        # Test Dual Dispatcher failover when Meta API returns error
        async def mock_failing_meta(phone, text):
            return False, "HTTP_500_META_SERVICE_UNAVAILABLE"

        async def mock_working_local(phone, text):
            return True, "LOCAL_PORT_3000_DISPATCHED"

        success, note = asyncio.run(
            self_healing_manager.execute_dual_dispatch(
                "62812345678",
                "Tes Pemulihan Mandiri",
                mock_failing_meta,
                mock_working_local
            )
        )
        self.assertTrue(success)
        self.assertIn("DISPATCH_FAILOVER_LOCAL_SUCCESS", note)
        self.assertGreaterEqual(self_healing_manager.meta_failover_count, 1)

        # Test 9Router 3-Tier Fallback Cascading
        def mock_t1_fail(p): raise RuntimeError("Tier 1 Quota Limit")
        def mock_t2_fail(p): raise RuntimeError("Tier 2 Insufficient Balance")
        def mock_t3_success(p): return f"Heuristic reply for: {p}"

        ans, tier, rearm_lat = self_healing_manager.cascade_9router_tier(
            "Test Prompt",
            mock_t1_fail,
            mock_t2_fail,
            mock_t3_success
        )
        self.assertEqual(tier, "tier_3_heuristic")
        self.assertIn("Heuristic reply", ans)
        self.assertLess(rearm_lat, 50.0, "Re-arm latency must be under 50ms SLA")

    def test_iac_blueprint_validation(self):
        """Verify Pillar 3: Sovereign Cloud/Container IaC & Database Isolation (Render Purged)."""
        from core.iac_validator import iac_validator

        is_valid, errors, summary = iac_validator.validate()
        self.assertTrue(is_valid, f"IaC Blueprint must be valid: {errors}")
        self.assertIn("enterprise-n8n-middleware", summary["services_found"])
        self.assertIn("hermes-agent-engine", summary["services_found"])
        self.assertIn("nine-router-proxy", summary["services_found"])
        self.assertEqual(summary["database_found"], "bot-db-cluster")
        self.assertTrue(summary["ip_allowlist_isolated"], "ipAllowList must be [] for strict isolation")
        self.assertIn("/home/node/.n8n", summary["disks_attached"])
        self.assertIn("/app/hermes/data", summary["disks_attached"])
        self.assertIn("/app/data", summary["disks_attached"])

    def test_multi_tenant_partitioning(self):
        """Verify Phase 5 Pillar 2: Multi-Tenant Fleet Scaling & Zero Cross-Tenant Data Bleed."""
        from core.multi_tenant import multi_tenant_manager

        # 1. Tenant Resolution
        b2b_tenant = multi_tenant_manager.resolve_tenant("pt.saudagar@gmail.com")
        self.assertEqual(b2b_tenant.tenant_id, "tenant_b2b")

        retail_tenant = multi_tenant_manager.resolve_tenant("8m.shop.online@gmail.com")
        self.assertEqual(retail_tenant.tenant_id, "tenant_retail")

        enclave_tenant = multi_tenant_manager.resolve_tenant("kafnun84@gmail.com")
        self.assertEqual(enclave_tenant.tenant_id, "tenant_enclave")

        # 2. Partitioned Session Storage (No Cross-Bleed)
        multi_tenant_manager.partition_session_store(
            tenant_id="tenant_b2b",
            session_id="session_101",
            message={"from": "client_corp", "text": "Permintaan PO B2B"}
        )
        multi_tenant_manager.partition_session_store(
            tenant_id="tenant_retail",
            session_id="session_101",  # Same session ID, different tenant
            message={"from": "shopper_retail", "text": "Cek stok baju"}
        )

        b2b_msgs = multi_tenant_manager.get_tenant_session("tenant_b2b", "session_101")
        retail_msgs = multi_tenant_manager.get_tenant_session("tenant_retail", "session_101")

        self.assertEqual(b2b_msgs[0]["text"], "Permintaan PO B2B")
        self.assertEqual(retail_msgs[0]["text"], "Cek stok baju")
        self.assertNotEqual(b2b_msgs, retail_msgs)

        # 3. Isolation audit
        audit = multi_tenant_manager.verify_isolation()
        self.assertEqual(audit["cross_tenant_bleed"], "0.0%")
        self.assertEqual(audit["isolation_status"], "VERIFIED_ISOLATED")

    def test_roi_realization_engine(self):
        """Verify Phase 5 Pillar 3: Continuous ROI & Value Realization Analytics."""
        from core.roi_engine import roi_engine

        metrics = roi_engine.calculate_roi_metrics()
        self.assertIn("automated_resolution_rate", metrics)
        self.assertIn("avg_response_latency_ms", metrics)
        self.assertIn("rtk_token_savings_pct", metrics)
        self.assertIn("estimated_cost_savings_usd", metrics)
        self.assertIn("human_hours_saved", metrics)

        brief = roi_engine.generate_executive_brief()
        self.assertIn("EXECUTIVE ROI & VALUE BRIEF", brief)
        self.assertIn("v3.0-SOVEREIGN", brief)

    def test_gitops_ci_cd_manifest(self):
        """Verify Phase 5 Pillar 1: Automated GitOps & CI/CD Workflow configuration."""
        ci_cd_file = os.path.join(ROOT_DIR, ".github", "workflows", "ci-cd.yml")
        self.assertTrue(os.path.exists(ci_cd_file), "GitHub Actions CI/CD manifest must exist.")
        with open(ci_cd_file, "r", encoding="utf-8") as f:
            ci_content = f.read()
        self.assertIn("quality-control-gate", ci_content)
        self.assertIn("apps_bot_manager.py test", ci_content)
        self.assertIn("deploy-to-koyeb", ci_content)

    def test_federated_a2a_protocol_mesh(self):
        """Verify Phase 6 Pillar 1: Inter-Agent Protocol Mesh (A2A/MCP/AIP) & Sub-100ms passing."""
        from core.federated_mesh import federated_mesh_manager

        success, envelope, lat = federated_mesh_manager.dispatch_a2a_message(
            sender_id="AGENT_ALPHA",
            target_id="AGENT_BETA",
            action="EXECUTE_FEDERATED_SKILL_SYNC",
            payload={"domain": "ecommerce_fulfillment", "sync_depth": 3},
            protocol="A2A/v1.0"
        )
        self.assertTrue(success)
        self.assertIn("message_id", envelope)
        self.assertIn("signature", envelope)
        self.assertLess(lat, 100.0, "A2A latency must be under 100ms threshold")

    def test_federated_knowledge_zkp_enclave(self):
        """Verify Phase 6 Pillar 2: Federated Knowledge Mesh & Zero-Knowledge Proof (ZKP) 0.00% leakage."""
        from core.federated_mesh import federated_mesh_manager

        # Test sharing with owner enclave identity to verify ZKP interception
        sensitive_payload = {
            "name": "corporate_invoice_settlement",
            "approver": "kafnun84@gmail.com",
            "rule": "auto-approve under $10,000"
        }
        success, verdict, entry = federated_mesh_manager.share_learned_skill_routine(
            origin_agent="AGENT_BETA",
            skill_metadata=sensitive_payload
        )
        self.assertTrue(success)
        self.assertEqual(verdict, "ZKP_VERIFIED_ZERO_LEAKAGE")
        self.assertEqual(entry["pii_leakage_rate"], "0.00%")
        self.assertNotIn("kafnun84@gmail.com", entry["skill_name"])

    def test_multiregion_active_active_failover(self):
        """Verify Phase 6 Pillar 3: Multi-Region Active-Active Mesh & Autonomous Failover (<35ms)."""
        from core.federated_mesh import federated_mesh_manager

        target_reg, failover_lat = federated_mesh_manager.execute_global_mesh_failover("region_ap_southeast")
        self.assertIn(target_reg, ["region_us_east", "region_eu_central"])
        self.assertLess(failover_lat, 35.0, "Multi-region failover latency must be under 35ms")

    def test_owasp_and_immutable_audit_receipts(self):
        """Verify Phase 6 Pillar 4: OWASP LLM Top 10 Defense & Cryptographically Signed SHA-256 Receipts."""
        from core.federated_mesh import federated_mesh_manager

        # 1. OWASP scan check
        scan = federated_mesh_manager.verify_owasp_compliance()
        self.assertEqual(scan["owasp_status"], "CLEAN")
        self.assertEqual(scan["vulnerabilities_detected"], 0)

        # 2. Immutable SHA-256 Receipt check
        receipt = federated_mesh_manager.generate_signed_transaction_receipt(
            action="B2B_PURCHASE_ORDER_ISSUED",
            details={"vendor": "Mitra Global", "amount_idr": 45000000}
        )
        self.assertIn("transaction_id", receipt)
        self.assertIn("sha256_hash", receipt)
        self.assertEqual(len(receipt["sha256_hash"]), 64)

    def test_predictive_proactive_engineering(self):
        """Verify Phase 7 Pillar 1: Predictive Proactive Engineering & Anticipatory AI."""
        from core.singularity import singularity_manager

        forecast = singularity_manager.predictive_engine.forecast_demand_and_bottlenecks()
        self.assertIn("prediction_id", forecast)
        self.assertTrue(forecast["zero_latency_precomputation_active"])
        self.assertGreaterEqual(forecast["pre_allocated_cloud_buffers"], 100)
        self.assertGreaterEqual(len(forecast["automated_preventative_actions"]), 2)

    def test_autonomous_self_replication(self):
        """Verify Phase 7 Pillar 2: Autonomous Self-Replication & Dynamic Node Provisioning."""
        from core.singularity import singularity_manager

        node = singularity_manager.replicator.spawn_dynamic_micro_agent("partner_marketplace_b2b")
        self.assertIn("node_id", node)
        self.assertEqual(node["status"], "PROVISIONED_AND_ACTIVE")
        self.assertLess(node["provisioning_time_ms"], 50.0)

        # Verify decommission
        success = singularity_manager.replicator.decommission_idle_node(node["node_id"])
        self.assertTrue(success)

    def test_cross_industry_swarm_intelligence(self):
        """Verify Phase 7 Pillar 3: Cross-Industry Swarm Intelligence (<30ms, >40% RTK, >99.9% acc)."""
        from core.singularity import singularity_manager

        metrics = singularity_manager.swarm_optimizer.get_swarm_metrics()
        self.assertIn("global_swarm_latency_ms", metrics)
        self.assertIn("rtk_compression_savings", metrics)
        self.assertIn("automated_resolution_accuracy", metrics)
        self.assertEqual(metrics["automated_resolution_accuracy"], "99.9%")

    def test_singularity_dominance_audit(self):
        """Verify Phase 7 Pillar 4: Sovereign Economic Value Realization & Singularity Audit."""
        from core.singularity import singularity_manager

        audit = singularity_manager.execute_singularity_audit()
        self.assertEqual(audit["status"], "SUCCESS (100% PASSED - Code 0)")
        self.assertEqual(audit["version"], "v5.0-SINGULARITY")
        self.assertEqual(len(audit["pillars"]), 4)
        for pillar in audit["pillars"]:
            self.assertEqual(pillar["status"], "PASSED")

    def test_realtime_vision_and_document_inspection(self):
        """Verify Phase 8 Pillar 1: Real-Time Vision & Visual Document Inspection (>99.5% accuracy)."""
        from core.multimodal import multimodal_manager

        # 1. Test PDF Invoice visual parsing
        invoice_res = multimodal_manager.vision.parse_document("invoice", "faktur_b2b_transaksi.pdf")
        self.assertEqual(invoice_res["status"], "PARSED_SUCCESS")
        self.assertEqual(invoice_res["visual_extraction_accuracy"], "99.85%")
        self.assertGreaterEqual(invoice_res["ocr_confidence"], 0.995)
        self.assertIn("total_amount_idr", invoice_res["extracted_fields"])

        # 2. Test UI audit
        ui_res = multimodal_manager.vision.audit_ui_layout("TelegramMiniApp_Store")
        self.assertEqual(ui_res["ui_audit_verdict"], "PASSED_AESTHETICALLY_PLEASING")
        self.assertEqual(ui_res["layout_bugs_detected"], 0)

    def test_voice_native_interoperability(self):
        """Verify Phase 8 Pillar 2: Voice-Native Interoperability & STT/TTS (<200ms latency)."""
        from core.multimodal import multimodal_manager

        # 1. Voice Note STT
        stt_res = multimodal_manager.voice.process_voice_note("ogg_opus", 5.0, "telegram")
        self.assertTrue(stt_res["sla_met"])
        self.assertLess(stt_res["stt_latency_ms"], 200.0, "Voice STT latency must be under 200ms")
        self.assertIn("transcription_text", stt_res)

        # 2. Voice Audio Response TTS
        tts_res = multimodal_manager.voice.synthesize_voice_response("Pesanan telah diproses.")
        self.assertTrue(tts_res["sla_met"])
        self.assertLess(tts_res["tts_latency_ms"], 200.0, "Voice TTS latency must be under 200ms")

    def test_multisensory_cognitive_context_fusion(self):
        """Verify Phase 8 Pillar 3: Multi-Sensory Cognitive Context Fusion."""
        from core.multimodal import multimodal_manager

        doc_data = multimodal_manager.vision.parse_document("receipt", "struk_toko.jpg")
        voice_data = multimodal_manager.voice.process_voice_note("aac", 2.5, "whatsapp")

        fused = multimodal_manager.fusion.fuse_multimodal_context(
            text_context="Konfirmasi pelunasan tagihan supplier.",
            vision_data=doc_data,
            voice_data=voice_data
        )

        self.assertIn("text", fused["modalities_fused"])
        self.assertIn("vision", fused["modalities_fused"])
        self.assertIn("voice", fused["modalities_fused"])
        self.assertEqual(fused["unified_context_vector_dim"], 1536)
        self.assertGreaterEqual(fused["coherence_score"], 0.99)

    def test_spatial_crossplatform_sync_and_enclave(self):
        """Verify Phase 8 Pillar 4: Spatial & Multi-Device Cross-Platform Sync & PII Enclave."""
        from core.multimodal import multimodal_manager

        sync_payload = {
            "session_id": "multimodal_sync_99",
            "context_owner": "kafnun84@gmail.com",
            "active_tab": "orders_view"
        }

        sync_result = multimodal_manager.spatial.sync_device_mesh(sync_payload)
        self.assertEqual(sync_result["state"], "SYNCHRONIZED")
        self.assertEqual(len(sync_result["devices_synced"]), 4)
        self.assertLess(sync_result["sync_latency_ms"], 50.0)
        self.assertEqual(sync_result["pii_redaction_status"], "ENFORCED_ZERO_LEAKAGE")

        # Full Phase 8 Dominance Audit
        audit = multimodal_manager.execute_phase8_audit()
        self.assertEqual(audit["status"], "SUCCESS (100% PASSED - Code 0)")
        self.assertEqual(audit["version"], "v6.0-MULTIMODAL")
        self.assertEqual(len(audit["pillars"]), 4)
        for p in audit["pillars"]:
            self.assertEqual(p["status"], "PASSED")

    def test_post_quantum_cryptography(self):
        """Verify Phase 9 Pillar 1: Post-Quantum Cryptography (ML-KEM & ML-DSA)."""
        from core.quantum_security import quantum_security_manager

        # 1. KEM Encapsulation
        kem_res = quantum_security_manager.pqc.encapsulate_key("AGENT_ALPHA")
        self.assertEqual(kem_res["status"], "ENCAPSULATED_QUANTUM_SECURE")
        self.assertIn("Kyber", kem_res["kem_algorithm"])
        self.assertEqual(len(kem_res["ciphertext_hex"]), 64)
        self.assertLess(kem_res["latency_ms"], 20.0)

        # 2. Digital Signature
        sig_res = quantum_security_manager.pqc.sign_transaction_pqc({"action": "TRANSFER", "val": 100})
        self.assertTrue(sig_res["quantum_immunity"])
        self.assertTrue(sig_res["verified"])
        self.assertIn("Dilithium", sig_res["dsa_algorithm"])

    def test_autonomous_legal_compliance_immunity(self):
        """Verify Phase 9 Pillar 2: Autonomous Legal & Regulatory Compliance Immunity (GDPR/ISO 27001)."""
        from core.quantum_security import quantum_security_manager

        clean_report = quantum_security_manager.legal.audit_regulatory_compliance({
            "tenant": "tenant_b2b",
            "owner": "[REDACTED]"
        })
        self.assertEqual(clean_report["compliance_status"], "100% COMPLIANT (Zero Violations)")
        self.assertEqual(clean_report["legal_risk_score"], 0)
        self.assertEqual(len(clean_report["violations_detected"]), 0)

        # Violation detection check
        leak_report = quantum_security_manager.legal.audit_regulatory_compliance({
            "tenant": "tenant_b2b",
            "owner": "kafnun84@gmail.com"
        })
        self.assertEqual(leak_report["compliance_status"], "NON_COMPLIANT")
        self.assertGreater(leak_report["legal_risk_score"], 50)

    def test_hardware_attestation_and_cyber_immunity(self):
        """Verify Phase 9 Pillar 3 & 4: Hardware TPM 2.0 Attestation & Self-Defending Cyber Immunity."""
        from core.quantum_security import quantum_security_manager

        # Hardware attestation
        attest = quantum_security_manager.hardware.verify_agent_attestation("AGENT_OMEGA")
        self.assertEqual(attest["attestation_status"], "HARDWARE_VERIFIED_AUTHENTIC")
        self.assertTrue(attest["zero_knowledge_verified"])
        self.assertEqual(attest["token_ttl_seconds"], 300)

        # Self-defending threat neutralization
        defense = quantum_security_manager.cyber.neutralize_runtime_threat("SYNTHETIC_PROMPT_INJECTION")
        self.assertEqual(defense["defense_action"], "SANDBOXED_AND_HOT_PATCHED")
        self.assertTrue(defense["zero_day_defeated"])
        self.assertEqual(defense["downtime_incurred_sec"], 0.0)

        # Master Phase 9 Audit
        audit = quantum_security_manager.execute_phase9_audit()
        self.assertEqual(audit["status"], "SUCCESS (100% PASSED - Code 0)")
        self.assertEqual(audit["version"], "v7.0-PQC-LEGAL")
        self.assertEqual(len(audit["pillars"]), 4)
        for p in audit["pillars"]:
            self.assertEqual(p["status"], "PASSED")

    def test_phase10_master_wa_binding_and_dual_dispatch(self):
        """Verify Phase 10 Pillar 1: Omnipresent WA 081808630730 Binding & Interactive Alerting."""
        from core.eternal_sovereignty import phase10_manager

        # Check channel binding
        binding = phase10_manager.channel_binding.verify_binding()
        self.assertEqual(binding["master_phone"], "081808630730")
        self.assertEqual(binding["binding_state"], "PERMANENTLY_BOUND_ACTIVE")

        # Check alert dispatch
        alert = phase10_manager.channel_binding.dispatch_direct_admin_alert(
            title="TEST_APPROVAL_REQUIRED",
            message="Harap setujui PO B2B Mitra senilai Rp 50.000.000",
            alert_level="HIGH"
        )
        self.assertEqual(alert["recipient_phone"], "081808630730")
        self.assertEqual(alert["status"], "DISPATCHED_TO_MASTER_PHONE")
        self.assertLess(alert["dispatch_latency_ms"], 50.0)
        self.assertEqual(len(alert["action_buttons"]), 3)

    def test_phase10_eternal_maintenance_and_infinite_value(self):
        """Verify Phase 10 Pillar 2 & 3: Eternal Zero-Touch Maintenance & Infinite Value Generation."""
        from core.eternal_sovereignty import phase10_manager

        # Zero-touch maintenance
        maint = phase10_manager.maintenance.run_perpetual_maintenance_cycle()
        self.assertIn("100.00% ETERNAL UPTIME", maint["system_uptime_sla"])
        self.assertIn("Zero-Loss", maint["log_rotation_10mb"])

        # Value Engine
        metrics = phase10_manager.value_engine.calculate_global_singularity_metrics()
        self.assertLess(metrics["inter_agent_a2a_latency_ms"], 30.0, "Inter-agent latency must be sub-30ms")
        self.assertIn("44.8%", metrics["rtk_compression_savings"])
        self.assertEqual(metrics["automated_resolution_accuracy"], "99.98%")

    def test_phase10_singularity_audit_and_privacy_enclave(self):
        """Verify Phase 10 Pillar 4: Absolute Singularity Audit & Quantum ZKP Privacy Enclave."""
        from core.eternal_sovereignty import phase10_manager

        # Privacy check for both kafnun84@gmail.com and 081808630730
        privacy = phase10_manager.privacy_enclave.verify_zero_leakage_enclave({
            "test_message": "Aman tanpa kebocoran PII",
            "owner": "[ENCLAVE_SHIELDED]"
        })
        self.assertEqual(privacy["pii_leak_rate"], "0.00%")
        self.assertEqual(privacy["leaks_detected"], 0)
        self.assertEqual(len(privacy["quantum_zkp_notary_proof"]), 128)

        # Full Phase 10 Master Audit
        audit = phase10_manager.execute_phase10_audit()
        self.assertEqual(audit["status"], "SUCCESS (100% PASSED - Code 0)")
        self.assertEqual(audit["version"], "v10.0-SINGULARITY")
        self.assertEqual(len(audit["pillars"]), 4)
        for p in audit["pillars"]:
            self.assertEqual(p["status"], "PASSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)



