from __future__ import annotations

from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter()
service = ChatService()

@router.post("/ask", response_model=ChatResponse)
def ask_question(request: ChatRequest) -> ChatResponse:
    try:
        result = service.answer(request.question)
        return ChatResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
