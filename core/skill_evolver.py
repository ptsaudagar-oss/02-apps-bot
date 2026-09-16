"""
Skill Evolver & Creation Loop for APPS_BOT (Hermes Engine - Pillar 1).
Monitors multi-step reasoning workflows (5+ turns), extracts successful execution patterns,
and dynamically synthesizes modular SKILL.md documents following agentskills.io standard format.
Supports hot in-memory dynamic indexing without service restarts.
"""

import os
import yaml
from typing import Dict, Any, List, Optional
from datetime import datetime
from core.config import ROOT_DIR
from core.logger import setup_logger

logger = setup_logger("SKILL_EVOLVER")

SKILLS_DIR = os.path.join(ROOT_DIR, "skills")
os.makedirs(SKILLS_DIR, exist_ok=True)


class SkillCreationLoop:
    """Hermes Self-Improving Skill Loop."""

    def __init__(self, skills_dir: str = SKILLS_DIR):
        self.skills_dir = skills_dir
        self._dynamic_index: Dict[str, Dict[str, Any]] = {}
        self.reindex_skills()

    def reindex_skills(self) -> int:
        """Dynamically scans skills directory and hot-indexes all SKILL.md files."""
        indexed_count = 0
        if not os.path.exists(self.skills_dir):
            os.makedirs(self.skills_dir, exist_ok=True)
            return 0

        for root, _, files in os.walk(self.skills_dir):
            for file in files:
                if file.endswith(".md"):
                    skill_path = os.path.join(root, file)
                    try:
                        with open(skill_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        
                        skill_name = os.path.splitext(file)[0].lower()
                        metadata = self._parse_skill_metadata(content)
                        self._dynamic_index[skill_name] = {
                            "name": metadata.get("name", skill_name),
                            "description": metadata.get("description", ""),
                            "version": metadata.get("version", "1.0.0"),
                            "path": skill_path,
                            "indexed_at": datetime.now().isoformat()
                        }
                        indexed_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to index skill {skill_path}: {e}")

        logger.info(f"Dynamic skill indexing complete. Total active skills: {indexed_count}")
        return indexed_count

    def _parse_skill_metadata(self, content: str) -> Dict[str, Any]:
        """Extracts YAML frontmatter if present or inspects markdown headers."""
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    return yaml.safe_load(parts[1]) or {}
                except Exception:
                    pass
        return {"name": "unnamed_skill", "description": "Auto-extracted procedural skill"}

    def evaluate_workflow(self, turns: List[Dict[str, str]], skill_name: str, domain: str = "general") -> Optional[str]:
        """
        Evaluates multi-turn reasoning workflows (5+ turns).
        If workflow meets criteria, automatically synthesizes an agentskills.io standard SKILL.md file.
        """
        if len(turns) < 5:
            logger.debug(f"Workflow turns count ({len(turns)}) below threshold (5). Skipping synthesis.")
            return None

        # Build clean YAML frontmatter & markdown content
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        safe_name = skill_name.lower().replace(" ", "-").replace("_", "-")
        skill_filename = f"{safe_name}.md"
        skill_filepath = os.path.join(self.skills_dir, skill_filename)

        # Synthesize procedure steps from turns
        steps_markdown = []
        for i, turn in enumerate(turns, 1):
            role = turn.get("role", "agent").capitalize()
            action = turn.get("action", turn.get("content", ""))[:120].replace("\n", " ")
            steps_markdown.append(f"{i}. **{role} Step**: {action}")

        steps_content = "\n".join(steps_markdown)

        skill_document = (
            f"---\n"
            f"name: {safe_name}\n"
            f"description: Automatically synthesized procedural rule for {domain} workflow\n"
            f"version: 1.0.0\n"
            f"standard: agentskills.io/v1\n"
            f"created_at: \"{timestamp}\"\n"
            f"turns_analyzed: {len(turns)}\n"
            f"---\n\n"
            f"# 📜 Skill: {safe_name}\n\n"
            f"> **Domain**: `{domain}` | **Extracted via**: Hermes Skill Creation Loop (Pillar 1)\n\n"
            f"## 📋 Procedural Execution Workflow\n"
            f"{steps_content}\n\n"
            f"## 🛡️ Guardrails & Operational Constraints\n"
            f"- Verify inputs before triggering actions.\n"
            f"- Enforce latency ACK SLA <150ms.\n"
            f"- Maintain PII Redaction for sensitive identifiers.\n"
        )

        try:
            with open(skill_filepath, "w", encoding="utf-8") as f:
                f.write(skill_document)
            logger.info(f"✨ New skill '{safe_name}' successfully synthesized at: {skill_filepath}")
            
            # Hot re-index in memory
            self._dynamic_index[safe_name] = {
                "name": safe_name,
                "description": f"Automatically synthesized procedural rule for {domain} workflow",
                "version": "1.0.0",
                "path": skill_filepath,
                "indexed_at": datetime.now().isoformat()
            }
            return skill_filepath
        except Exception as e:
            logger.error(f"Failed to write synthesized skill file: {e}")
            return None

    def get_skill_index(self) -> Dict[str, Dict[str, Any]]:
        """Returns in-memory hot index of all active skills."""
        return self._dynamic_index

    def has_skill(self, skill_name: str) -> bool:
        return skill_name.lower().replace(" ", "-").replace("_", "-") in self._dynamic_index


skill_evolver = SkillCreationLoop()
