from pathlib import Path

from app.services.compliance_service import ComplianceService
from app.services.ticket_service import TicketService


def test_ticket_service_detects_maintenance_issue_and_persists_ticket(tmp_path: Path) -> None:
    storage_path = tmp_path / "demo_tickets.json"
    service = TicketService(storage_path=storage_path)

    result = service.build_ticket_suggestion(
        question="What caused the machine failure?",
        answer="The pump showed vibration and temperature issues during inspection.",
        context="Maintenance logs report a leak and a damaged seal.",
    )

    assert result["available"] is True
    assert result["ticket"]["priority"] == "High"
    assert result["ticket"]["category"] == "Maintenance"

    created = service.create_ticket(result["ticket"])
    assert created["status"] == "Open"
    assert created["problem"].startswith("Pump") or "vibration" in created["problem"].lower()

    tickets = service.list_tickets()
    assert len(tickets) == 1


def test_compliance_service_evaluates_sop_context(tmp_path: Path) -> None:
    rules_path = tmp_path / "compliance_rules.json"
    service = ComplianceService(rules_path=rules_path)

    result = service.evaluate_context(
        "This SOP manual outlines safety procedures and inspection guidelines for the plant."
    )

    assert result["applicable"] is True
    assert result["score"] >= 0
    assert result["status"] in {"PASS", "WARNING", "FAIL"}
    assert result["passed_checks"]
    assert result["missing_checks"] or result["passed_checks"]
