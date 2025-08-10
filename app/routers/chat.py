from fastapi import APIRouter
from pydantic import BaseModel
from app.services.agent_chat import build_agent

router = APIRouter(prefix="/v1/chat", tags=["chat"])


class ChatIn(BaseModel):
    username: str = "Nidhi"
    message: str


@router.post("/ask")
async def chat_ask(body: ChatIn):
    try:
        agent = build_agent(username=body.username)
        result = await agent.invoke_async(body.message)
        reply = str(result)
        return {"ok": True, "reply": reply}
    except Exception as e:
        return {"ok": False, "error": str(e)}
