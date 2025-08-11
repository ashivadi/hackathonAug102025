from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.models.goal import Goal
from app.core.config import settings

router = APIRouter(tags=["goals"])
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


@router.get("/goals", response_class=HTMLResponse)
def goals_page(request: Request, db: Session = Depends(get_db)):
    ensure_user(db)
    goals = db.query(Goal).order_by(Goal.horizon.asc(), Goal.created_at.asc()).all()
    return templates.TemplateResponse(
        "goals.html", {"request": request, "goals": goals}
    )


@router.get("/v1/goals/fragment", response_class=HTMLResponse)
def goals_fragment(request: Request, db: Session = Depends(get_db)):
    ensure_user(db)
    goals = db.query(Goal).order_by(Goal.horizon.asc(), Goal.created_at.asc()).all()
    return templates.TemplateResponse(
        "_goals_table.html", {"request": request, "goals": goals}
    )


class GoalIn(BaseModel):
    horizon: str
    text: str
    metric: Optional[str] = None
    target: Optional[float] = None


@router.post("/v1/goals", response_class=HTMLResponse)
def create_goal(req: GoalIn, request: Request, db: Session = Depends(get_db)):
    user = ensure_user(db)
    g = Goal(
        user_id=user.id,
        horizon=req.horizon,
        text=req.text,
        metric=req.metric,
        target=req.target,
    )
    db.add(g)
    db.commit()
    return goals_fragment(request, db)


class GoalPatch(BaseModel):
    horizon: Optional[str] = None
    text: Optional[str] = None
    metric: Optional[str] = None
    target: Optional[float] = None


@router.patch("/v1/goals/{goal_id}", response_class=HTMLResponse)
def update_goal(
    goal_id: int, req: GoalPatch, request: Request, db: Session = Depends(get_db)
):
    ensure_user(db)
    g = db.get(Goal, goal_id)
    if not g:
        return goals_fragment(request, db)
    if req.horizon is not None:
        g.horizon = req.horizon
    if req.text is not None:
        g.text = req.text
    if req.metric is not None:
        g.metric = req.metric
    if req.target is not None:
        g.target = req.target
    db.commit()
    return goals_fragment(request, db)


@router.delete("/v1/goals/{goal_id}", response_class=HTMLResponse)
def delete_goal(goal_id: int, request: Request, db: Session = Depends(get_db)):
    ensure_user(db)
    g = db.get(Goal, goal_id)
    if g:
        db.delete(g)
        db.commit()
    return goals_fragment(request, db)
