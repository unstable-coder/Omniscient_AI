from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.ticket_service import TicketService

router = APIRouter()
service = ChatService()
ticket_service = TicketService()

@router.post("/ask", response_model=ChatResponse)
def ask_question(request: ChatRequest) -> ChatResponse:
    try:
        result = service.answer(request.question)
        return ChatResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/tickets")
def list_demo_tickets() -> list[dict[str, Any]]:
    try:
        return ticket_service.list_tickets()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/tickets")
def create_demo_ticket(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        return ticket_service.create_ticket(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
