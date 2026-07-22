from __future__ import annotations

from fastapi import APIRouter, HTTPException
from app.services.ticket_service import TicketService

router = APIRouter()
ticket_service = TicketService()


@router.get("")
def list_demo_tickets() -> list[dict[str, object]]:
    try:
        return ticket_service.list_tickets()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
