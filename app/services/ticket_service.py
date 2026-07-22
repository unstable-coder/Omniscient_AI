from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TicketService:
    """Demo-only ticketing service for hackathon enterprise workflows.

    The implementation is intentionally simple and modular so it can later be
    swapped for Jira, ServiceNow, SAP, or ERP integrations without changing the
    surrounding chat UI.
    """

    MAINTENANCE_KEYWORDS = (
        "fault",
        "failure",
        "vibration",
        "temperature",
        "leak",
        "damage",
        "inspection",
        "maintenance",
        "alarm",
    )

    EQUIPMENT_HINTS = {
        "pump": "Pump System",
        "turbine": "Turbine Unit",
        "valve": "Valve Assembly",
        "motor": "Motor Assembly",
        "conveyor": "Conveyor Line",
        "compressor": "Compressor Station",
        "generator": "Generator Set",
        "boiler": "Boiler System",
        "sensor": "Sensor Network",
        "line": "Production Line",
    }

    def __init__(self, storage_path: str | Path | None = None) -> None:
        self.storage_path = Path(storage_path or Path(__file__).resolve().parents[2] / "storage" / "demo_tickets.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text("[]", encoding="utf-8")

    def detect_maintenance_issue(self, question: str, answer: str, context: str) -> bool:
        text = " ".join([question, answer, context]).lower()
        return any(keyword in text for keyword in self.MAINTENANCE_KEYWORDS)

    def build_ticket_suggestion(self, question: str, answer: str, context: str) -> dict[str, Any]:
        detected = self.detect_maintenance_issue(question, answer, context)
        if not detected:
            return {"available": False, "ticket": None}

        normalized_context = " ".join([question, answer, context])
        equipment = "Unknown Equipment"
        for hint, label in self.EQUIPMENT_HINTS.items():
            if hint in normalized_context.lower():
                equipment = label
                break

        priority = "High" if any(keyword in normalized_context.lower() for keyword in ["fault", "failure", "alarm", "leak", "damage"]) else "Medium"
        problem_text = answer.strip() or context.strip()[:180]
        if len(problem_text) > 180:
            problem_text = problem_text[:177] + "..."

        ticket = {
            "equipment": equipment,
            "priority": priority,
            "category": "Maintenance",
            "problem": f"{problem_text}",
            "recommendation": "Inspect the affected asset, verify operating conditions, and review recent maintenance logs.",
            "assigned_team": "Maintenance Operations",
            "status": "Open",
        }

        return {"available": True, "ticket": ticket}

    def create_ticket(self, ticket: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "id": self._next_id(),
            "equipment": ticket.get("equipment", "Unknown Equipment"),
            "priority": ticket.get("priority", "Medium"),
            "category": ticket.get("category", "Maintenance"),
            "problem": ticket.get("problem", "No problem description provided"),
            "recommendation": ticket.get("recommendation", "Review incident details"),
            "assigned_team": ticket.get("assigned_team", "Maintenance Operations"),
            "status": ticket.get("status", "Open"),
        }
        tickets = self.list_tickets()
        tickets.append(payload)
        self._write_tickets(tickets)
        return payload

    def list_tickets(self) -> list[dict[str, Any]]:
        try:
            return json.loads(self.storage_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def _write_tickets(self, tickets: list[dict[str, Any]]) -> None:
        self.storage_path.write_text(json.dumps(tickets, indent=2), encoding="utf-8")

    def _next_id(self) -> int:
        tickets = self.list_tickets()
        if not tickets:
            return 1
        return max(int(item.get("id", 0)) for item in tickets) + 1
