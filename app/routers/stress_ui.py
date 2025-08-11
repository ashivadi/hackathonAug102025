from __future__ import annotations
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.models.stressor import Stressor
from app.core.config import settings

router = APIRouter(tags=["stress"])
templates = Jinja2Templates(directory="app/templates")


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


@router.get("/stress", response_class=HTMLResponse)
def stress_page(request: Request, db: Session = Depends(get_db)):
    ensure_user(db)
    items = db.query(Stressor).order_by(Stressor.id.asc()).all()
    return templates.TemplateResponse(
        "stress.html", {"request": request, "items": items}
    )


@router.get("/v1/stress/fragment", response_class=HTMLResponse)
def stress_fragment(request: Request, db: Session = Depends(get_db)):
    ensure_user(db)
    items = db.query(Stressor).order_by(Stressor.id.asc()).all()
    return templates.TemplateResponse(
        "_stress_table.html", {"request": request, "items": items}
    )


class StressIn(BaseModel):
    trigger: str
    pattern: str | None = None
    coping: str | None = None


@router.post("/v1/stress", response_class=HTMLResponse)
def create_stress(req: StressIn, request: Request, db: Session = Depends(get_db)):
    user = ensure_user(db)
    db.add(
        Stressor(
            user_id=user.id, trigger=req.trigger, pattern=req.pattern, coping=req.coping
        )
    )
    db.commit()
    return stress_fragment(request, db)


class StressPatch(BaseModel):
    trigger: str | None = None
    pattern: str | None = None
    coping: str | None = None


@router.patch("/v1/stress/{sid}", response_class=HTMLResponse)
def update_stress(
    sid: int, req: StressPatch, request: Request, db: Session = Depends(get_db)
):
    ensure_user(db)
    s = db.get(Stressor, sid)
    if not s:
        return stress_fragment(request, db)
    if req.trigger is not None:
        s.trigger = req.trigger
    if req.pattern is not None:
        s.pattern = req.pattern
    if req.coping is not None:
        s.coping = req.coping
    db.commit()
    return stress_fragment(request, db)


@router.delete("/v1/stress/{sid}", response_class=HTMLResponse)
def delete_stress(sid: int, request: Request, db: Session = Depends(get_db)):
    ensure_user(db)
    s = db.get(Stressor, sid)
    if s:
        db.delete(s)
        db.commit()
    return stress_fragment(request, db)
