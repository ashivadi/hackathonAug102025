from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.models.goal import Goal
from app.core.config import settings

router = APIRouter(prefix="/v1/goals", tags=["goals"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_user(db: Session) -> User:
    u = db.query(User).first()
    if not u:
        u = User(email="you@example.com", tz=settings.default_tz)
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


@router.get("/list")
def list_goals(db: Session = Depends(get_db)):
    u = ensure_user(db)
    gs = (
        db.query(Goal)
        .filter(Goal.user_id == u.id)
        .order_by(Goal.horizon.asc(), Goal.created_at.asc())
        .all()
    )
    return {
        "ok": True,
        "data": [
            {
                "horizon": g.horizon,
                "text": g.text,
                "metric": g.metric,
                "target": g.target,
            }
            for g in gs
        ],
    }
