from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import hashlib
from app.db.session import SessionLocal
from app.models.user import User
from app.models.message import Message

router = APIRouter(prefix="/v1/inbox", tags=["inbox"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def quick_intent(subject: str | None, body: str | None):
    text = f"{subject or ''} {body or ''}".lower()
    if any(k in text for k in ["dinner","lunch","meet","coffee","tomorrow","tonight"]): return "invite"
    if any(k in text for k in ["todo","task","please do","action"]): return "task"
    return "fyi"

@router.post("/webhook")
async def inbox_webhook(payload: dict, db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user: return {"ok": False, "error": "No user"}
    subject = payload.get("subject"); body = payload.get("body")
    body_hash = hashlib.sha256((body or "").encode()).hexdigest()
    intent = quick_intent(subject, body)
    msg = Message(user_id=user.id, channel=payload.get("channel","email"), from_addr=payload.get("from"),
                  subject=subject, body_hash=body_hash, intent=intent, data=payload)
    db.add(msg); db.commit()
    return {"ok": True, "data": {"id": msg.id, "intent": intent}}
