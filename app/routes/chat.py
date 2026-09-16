from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.chatbot_engine import chatbot_engine

router = APIRouter()


class ChatInput(BaseModel):
    message: str | list[str] = Field(..., description="Single message or list of messages")
    user_id: str | None = None


@router.post("/conversation", summary="Get conversational shopping response")
async def chat(input: ChatInput):
    try:
        if isinstance(input.message, str):
            reply = await chatbot_engine.get_response(input.message, user_id=input.user_id)
            return {"reply": reply}
        if isinstance(input.message, list):
            replies = await chatbot_engine.get_batch_response(input.message, user_id=input.user_id)
            return {"replies": replies}
        raise HTTPException(status_code=400, detail="Invalid input format")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {e}")
