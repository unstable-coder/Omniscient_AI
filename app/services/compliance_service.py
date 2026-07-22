from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ComplianceService:
    """Demo-only compliance checker for SOPs, manuals, policies, and guidelines."""

    COMPLIANCE_CONTEXT_KEYWORDS = ("sop", "manual", "policy", "guideline", "procedure", "standard", "regulation")

    def __init__(self, rules_path: str | Path | None = None) -> None:
        self.rules_path = Path(rules_path or Path(__file__).resolve().parents[2] / "storage" / "compliance_rules.json")
        self.rules_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.rules_path.exists():
            self.rules_path.write_text(
                json.dumps(
                    {
                        "checks": [
                            {"id": "safety", "label": "Safety procedures documented", "keywords": ["safety", "hazard", "risk"]},
                            {"id": "inspection", "label": "Inspection routine defined", "keywords": ["inspection", "check", "routine"]},
                            {"id": "response", "label": "Emergency response guidance included", "keywords": ["emergency", "response", "incident"]},
                            {"id": "training", "label": "Training expectations described", "keywords": ["training", "competency", "operator"]},
                        ]
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

    def should_offer_compliance(self, text: str) -> bool:
        normalized_text = text.lower()
        return any(keyword in normalized_text for keyword in self.COMPLIANCE_CONTEXT_KEYWORDS)

    def evaluate_context(self, context: str) -> dict[str, Any]:
        if not self.should_offer_compliance(context):
            return {
                "applicable": False,
                "score": 0,
                "status": "FAIL",
                "passed_checks": [],
                "missing_checks": [],
                "suggested_improvements": ["No compliance checklist is available for this context."],
            }

        normalized_context = context.lower()
        rules = self._load_rules()
        checks = rules.get("checks", [])

        passed_checks: list[str] = []
        missing_checks: list[str] = []

        for check in checks:
            labels = check.get("keywords", [])
            if any(keyword.lower() in normalized_context for keyword in labels):
                passed_checks.append(check.get("label", check.get("id", "check")))
            else:
                missing_checks.append(check.get("label", check.get("id", "check")))

        total = max(len(checks), 1)
        score = round((len(passed_checks) / total) * 100)
        if score >= 80:
            status = "PASS"
        elif score >= 50:
            status = "WARNING"
        else:
            status = "FAIL"

        suggestions = []
        if missing_checks:
            suggestions.append("Expand the document with explicit training, emergency response, and inspection guidance.")
        if status != "PASS":
            suggestions.append("Add a short compliance summary section to make audit readiness clearer.")
        if not suggestions:
            suggestions.append("No additional improvements required for this demo checklist.")

        return {
            "applicable": bool(checks),
            "score": score,
            "status": status,
            "passed_checks": passed_checks,
            "missing_checks": missing_checks,
            "suggested_improvements": suggestions,
        }

    def _load_rules(self) -> dict[str, Any]:
        try:
            return json.loads(self.rules_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"checks": []}
