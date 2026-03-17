"""AI chat assistant routes."""
import os
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from src.chat import chat as run_chat
from src.config import get_trip

router = APIRouter(tags=["chat"])
templates = Jinja2Templates(directory="templates")


class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = []


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request) -> HTMLResponse:
    trip = get_trip()
    return templates.TemplateResponse(
        "chat.html",
        {"request": request, "trip_name": trip.get("name", "Family Trip")},
    )


@router.post("/api/chat")
async def chat_endpoint(body: ChatRequest) -> JSONResponse:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return JSONResponse({"error": "ANTHROPIC_API_KEY not configured"}, status_code=503)

    try:
        trip = get_trip()
        reply = run_chat(body.message, body.history, trip)
        return JSONResponse({"reply": reply})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
