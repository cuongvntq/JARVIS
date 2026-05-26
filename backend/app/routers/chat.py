"""Chat endpoints (placeholder, full implementation in Sprint 1-2)."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.llm.client import chat_completion

router = APIRouter()


class ChatRequest(BaseModel):
    content: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    content: str
    model_used: str


@router.post("/send", response_model=ChatResponse)
async def send_message(req: ChatRequest):
    """Sprint 1 placeholder — gọi LLM 1 chiều, chưa lưu DB, chưa tool calling."""
    messages = [
        {
            "role": "system",
            "content": (
                "Bạn là JARVIS, trợ lý cá nhân của người dùng. "
                "Giao tiếp bằng tiếng Việt tự nhiên, ngắn gọn (1-3 câu)."
            ),
        },
        {"role": "user", "content": req.content},
    ]
    response, model = await chat_completion(messages)
    return ChatResponse(content=response, model_used=model)
