from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.memory import upsert_preference
from app.models.user import User
from app.models.trait import Trait
from app.models.stressor import Stressor

router = APIRouter(prefix="/v1/memory", tags=["memory"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/upsert")
async def upsert(body: dict, db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user: return {"ok": False, "error": "No user"}
    kind = body.get("kind"); key = body.get("key")
    value = body.get("value"); conf = float(body.get("confidence", 0.8))
    if kind == "preference":
        upsert_preference(db, user.id, key, value, conf); db.commit(); return {"ok": True}
    if kind == "trait":
        t = Trait(user_id=user.id, key=key, value=value, confidence=conf); db.add(t); db.commit(); return {"ok": True}
    if kind == "stressor":
        s = Stressor(user_id=user.id, trigger=key, pattern=value.get("pattern"), coping=value.get("coping"), confidence=conf)
        db.add(s); db.commit(); return {"ok": True}
    return {"ok": False, "error": "Unknown kind"}
