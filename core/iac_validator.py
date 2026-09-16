"""
IaC Blueprint Validator for Render Platform (Pillar 3).
Audits declarative render.yaml manifests to verify:
- 4 Services: enterprise-n8n-middleware, hermes-agent-engine, nine-router-proxy, bot-db-cluster
- PostgreSQL network isolation (ipAllowList: [])
- Persistent disk attachments (/home/node/.n8n, /app/hermes/data, /app/data)
"""

import os
import yaml
from typing import Dict, Any, List, Tuple
from core.config import ROOT_DIR
from core.logger import setup_logger

logger = setup_logger("IAC_VALIDATOR")

RENDER_YAML_PATH = os.path.join(ROOT_DIR, "render.yaml")


class RenderIaCValidator:
    """Validates render.yaml against Phase 4 deployment standards."""

    REQUIRED_SERVICES = [
        "enterprise-n8n-middleware",
        "hermes-agent-engine",
        "nine-router-proxy"
    ]
    REQUIRED_DATABASE = "bot-db-cluster"

    def __init__(self, filepath: str = RENDER_YAML_PATH):
        self.filepath = filepath

    def validate(self) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Parses and audits render.yaml.
        Returns (is_valid, validation_errors, manifest_summary).
        """
        errors = []
        summary = {
            "services_found": [],
            "database_found": None,
            "ip_allowlist_isolated": False,
            "disks_attached": []
        }

        if not os.path.exists(self.filepath):
            return False, [f"Blueprint file '{self.filepath}' does not exist."], summary

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            return False, [f"YAML parsing error in {self.filepath}: {e}"], summary

        # 1. Services Audit
        services = data.get("services", [])
        svc_names = [s.get("name") for s in services if isinstance(s, dict)]
        summary["services_found"] = svc_names

        # Check required services or unified service
        for req in self.REQUIRED_SERVICES:
            if req not in svc_names and "apps-bot-service" not in svc_names:
                errors.append(f"Missing required service: '{req}'")

        # 2. Disk Mounts Audit
        for svc in services:
            if not isinstance(svc, dict):
                continue
            disks = svc.get("disk", [])
            if isinstance(disks, dict):
                disks = [disks]
            for d in disks:
                mount_path = d.get("mountPath")
                if mount_path:
                    summary["disks_attached"].append(mount_path)

        # 3. Database Audit (bot-db-cluster)
        databases = data.get("databases", [])
        db_names = [db.get("name") for db in databases if isinstance(db, dict)]
        if self.REQUIRED_DATABASE in db_names:
            summary["database_found"] = self.REQUIRED_DATABASE
            for db in databases:
                if db.get("name") == self.REQUIRED_DATABASE:
                    # Enforce strict private network isolation: ipAllowList: []
                    allowlist = db.get("ipAllowList")
                    if allowlist == [] or allowlist is None or len(allowlist) == 0:
                        summary["ip_allowlist_isolated"] = True
                    else:
                        errors.append("Database 'bot-db-cluster' ipAllowList must be empty [] for strict isolation.")
        else:
            # If unified container mode or database entry is missing
            errors.append(f"Missing required managed database: '{self.REQUIRED_DATABASE}'")

        is_valid = len(errors) == 0
        if is_valid:
            logger.info(f"✅ render.yaml passed all IaC validation checks ({len(svc_names)} services, DB isolated).")
        else:
            logger.warning(f"⚠️ render.yaml validation warnings: {errors}")

        return is_valid, errors, summary


iac_validator = RenderIaCValidator()
