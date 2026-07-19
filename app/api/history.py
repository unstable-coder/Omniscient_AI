from __future__ import annotations

from fastapi import APIRouter, HTTPException
from app.services.history_service import HistoryService
from app.models.schemas import ChatHistoryItem

router = APIRouter()
service = HistoryService()

@router.get("/history", response_model=list[ChatHistoryItem])
def get_history() -> list[ChatHistoryItem]:
    return service.read_history()

@router.delete("/history")
def clear_history() -> dict[str, str]:
    try:
        service.clear_history()
        return {"status": "ok", "message": "History cleared."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
