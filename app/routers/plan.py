from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.config import settings
from app.core.time import day_bounds
from app.models.user import User
from app.models.plan import Plan

# Reuse the SAME tools the chat agent uses
from app.services.agent_chat import (
    plan_today as tool_plan_today,
    suggest_next_actions as tool_suggest_next_actions,
    goal_summary as tool_goal_summary,
)

router = APIRouter(prefix="/v1/plan", tags=["plan"])
templates = Jinja2Templates(directory="app/templates")


# ---- DB helpers ----
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


@router.post("/run")
async def run_plan(db: Session = Depends(get_db)):
    """
    Build & SAVE today's plan using the same tools the chat uses.
    """
    user = ensure_user(db)

    # Same pipeline your chat calls
    _summary = tool_goal_summary()  # not saved; handy for UI toast if needed
    payload = await tool_plan_today()  # dict with eisenhower/schedule/etc.
    suggestions = tool_suggest_next_actions()  # extra nudges

    # Upsert today's saved plan
    start, end = day_bounds(user.tz)
    plan = (
        db.query(Plan)
        .filter(Plan.user_id == user.id, Plan.date >= start, Plan.date <= end)
        .one_or_none()
    )
    if not plan:
        plan = Plan(
            user_id=user.id,
            date=start,
            matrix=payload["eisenhower"],
            schedule=payload["schedule"],
            affirmations=payload.get("affirmations", {}),
            needles=payload.get("three_needles", {}),
            stress_guide=payload.get("stress_guide", []),
            nudges=(payload.get("nudges", []) + suggestions.get("advice", [])),
        )
        db.add(plan)
    else:
        plan.matrix = payload["eisenhower"]
        plan.schedule = payload["schedule"]
        plan.affirmations = payload.get("affirmations", {})
        plan.needles = payload.get("three_needles", {})
        plan.stress_guide = payload.get("stress_guide", [])
        plan.nudges = payload.get("nudges", []) + suggestions.get("advice", [])

    db.commit()
    db.refresh(plan)
    return {"ok": True, "planId": plan.id, "goalsSummary": _summary}


@router.get("/fragment", response_class=HTMLResponse)
async def plan_fragment(request: Request, db: Session = Depends(get_db)):
    """
    Build today's plan LIVE (same tools), but DO NOT save.
    Returns the rendered HTML partial so the homepage can swap it in without reload.
    """
    ensure_user(db)  # ensures tz etc.
    payload = await tool_plan_today()
    suggestions = tool_suggest_next_actions()

    # Build a "view model" (same shape the partials expect)
    view_plan = {
        "matrix": payload["eisenhower"],
        "schedule": payload["schedule"],
        "affirmations": payload.get("affirmations", {}),
        "needles": payload.get("three_needles", {}),
        "stress_guide": payload.get("stress_guide", []),
        "nudges": (payload.get("nudges", []) + suggestions.get("advice", [])),
    }

    # Render the same container partial you show on the homepage
    return templates.TemplateResponse(
        "_plan_container.html",
        {"request": request, "plan": view_plan},
    )
