from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.session import SessionLocal
from app.models.user import User
from app.models.event import Event
from app.services.google_calendar import sync_primary, create_event, update_event
from app.core.config import settings

router = APIRouter(prefix="/v1/calendar", tags=["calendar"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def ensure_user(db: Session) -> User:
    user = db.query(User).first()
    if not user:
        user = User(email="you@example.com", tz=settings.default_tz)
        db.add(user); db.commit(); db.refresh(user)
    return user

@router.post("/sync")
async def sync(db: Session = Depends(get_db)):
    user = ensure_user(db)
    count = sync_primary(db, user, days_forward=30)
    return {"ok": True, "synced": count}

@router.get("/events")
async def list_events(frm: str | None = Query(None), to: str | None = Query(None), db: Session = Depends(get_db)):
    user = ensure_user(db)
    q = db.query(Event).filter(Event.user_id == user.id)
    if frm:
        q = q.filter(Event.start >= datetime.fromisoformat(frm))
    if to:
        q = q.filter(Event.end <= datetime.fromisoformat(to))
    events = q.order_by(Event.start.asc()).limit(200).all()
    return {"ok": True, "data": events}

@router.post("/create")
async def create(body: dict, db: Session = Depends(get_db)):
    user = ensure_user(db)
    ev = create_event(
        db, user,
        summary=body["summary"],
        start_iso=body["start"],
        end_iso=body["end"],
        location=body.get("location"),
    )
    return {"ok": True, "data": {"external_id": ev.external_id}}

@router.post("/update")
async def patch(body: dict, db: Session = Depends(get_db)):
    user = ensure_user(db)
    external_id = body["external_id"]
    patch = body.get("patch", {})
    ev = update_event(db, user, external_id, patch)
    return {"ok": True, "data": {"external_id": ev.external_id}}
