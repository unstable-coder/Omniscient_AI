from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.api.admin import router as admin_router
from app.api.chat import router as chat_router
from app.api.history import router as history_router
from app.api.tickets import router as tickets_router
from app.routes.dashboard import router as dashboard_router
from pathlib import Path

app = FastAPI()

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

templates = Jinja2Templates(directory=Path(__file__).parent / "utils" / "templates")

app.include_router(admin_router, prefix="/api/admin")
app.include_router(chat_router, prefix="/api/chat")
app.include_router(history_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(tickets_router, prefix="/api/tickets")

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"request": request}
    )

@app.get("/chat")
def chat(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={"request": request}
    )

@app.get("/admin/tickets")
def ticket_admin(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="tickets.html",
        context={"request": request}
    )

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "running"}
