from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.core.config import settings
from app.services.google_calendar import start_oauth, finish_oauth

router = APIRouter(tags=["google-auth"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/auth/google/start")
async def auth_start(db: Session = Depends(get_db)):
    # single-user demo: ensure a user exists
    user = db.query(User).first()
    if not user:
        user = User(email="you@example.com", tz=settings.default_tz)
        db.add(user); db.commit(); db.refresh(user)
    url = start_oauth(state=user.id)
    return RedirectResponse(url)

@router.get("/auth/google/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    user = db.query(User).first()
    acct = finish_oauth(db, user, str(request.url))
    return {"ok": True, "connected": True, "provider": "google"}
