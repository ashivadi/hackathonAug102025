import os
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func
from strands import Agent, tool
from strands.models.anthropic import (
    AnthropicModel,
)  # pip install 'strands-agents[anthropic]'

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.models.task import Task
from app.models.goal import Goal
from app.models.stressor import Stressor
from app.services.memory import upsert_preference
from app.core.time import day_bounds
from app.models.event import Event
from app.services.planner import call_claude


# ---------- db helpers ----------
def _db() -> Session:
    return SessionLocal()


def _ensure_user(db: Session) -> User:
    u = db.query(User).first()
    if not u:
        u = User(email="you@example.com", tz=settings.default_tz)
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


# ---------- GOAL tools ----------
@tool
def upsert_goal(
    text: str,
    horizon: str = "long",
    metric: Optional[str] = None,
    target: Optional[float] = None,
) -> str:
    """
    Save or update a goal. 'horizon' can be 'short' or 'long' (also accepts 14d|90d|12m).
    """
    db = _db()
    user = _ensure_user(db)
    # naive de-dup: same text + horizon -> update; else insert
    g = (
        db.query(Goal)
        .filter(Goal.user_id == user.id, Goal.text == text, Goal.horizon == horizon)
        .one_or_none()
    )
    if not g:
        g = Goal(
            user_id=user.id, horizon=horizon, text=text, metric=metric, target=target
        )
        db.add(g)
    else:
        g.metric = metric
        g.target = target
    db.commit()
    return f"Saved goal ({horizon}): {text}"


@tool
def list_goals() -> Dict[str, List[Dict[str, Any]]]:
    """
    Return goals grouped by horizon for quick summary.
    """
    db = _db()
    user = _ensure_user(db)
    gs = (
        db.query(Goal)
        .filter(Goal.user_id == user.id)
        .order_by(Goal.horizon.asc(), Goal.created_at.asc())
        .all()
    )
    short = [
        {"text": g.text, "metric": g.metric, "target": g.target}
        for g in gs
        if (g.horizon or "").startswith("short") or g.horizon in ("14d", "90d")
    ]
    long = [
        {"text": g.text, "metric": g.metric, "target": g.target}
        for g in gs
        if (g.horizon or "").startswith("long") or g.horizon in ("12m",)
    ]
    other = [
        {"text": g.text, "metric": g.metric, "target": g.target}
        for g in gs
        if g not in []
    ]
    return {"short": short, "long": long, "other": other}


@tool
def goal_summary() -> str:
    """
    Human-friendly one-liner summary of short & long term goals.
    """
    groups = list_goals()
    s = []
    if groups["short"]:
        s.append("Short-term: " + "; ".join(g["text"] for g in groups["short"]))
    if groups["long"]:
        s.append("Long-term: " + "; ".join(g["text"] for g in groups["long"]))
    if not s:
        return "No goals saved yet."
    return " | ".join(s)


# ---------- Tasks & events helpers ----------
KEYWORDS_HEALTH = (
    "exercise",
    "workout",
    "run",
    "walk",
    "yoga",
    "skipping",
    "skip",
    "gym",
)
KEYWORDS_REL = (
    "dinner",
    "lunch",
    "coffee",
    "meet",
    "hangout",
    "call",
    "parents",
    "mom",
    "dad",
    "friend",
    "husband",
    "wife",
    "partner",
)


def _days_since_last(
    db: Session, user: User, keywords: tuple[str, ...]
) -> Optional[int]:
    """
    Naive heuristic: find latest calendar event whose summary contains any keyword.
    """
    ev = (
        db.query(Event)
        .filter(Event.user_id == user.id)
        .filter(
            func.lower(Event.summary).op("REGEXP")(
                f"({'|'.join(kw.lower() for kw in keywords)})"
            )
        )
        .order_by(Event.start.desc())
        .first()
    )
    if not ev or not ev.start:
        return None
    return (datetime.utcnow() - ev.start.replace(tzinfo=None)).days


@tool
def suggest_next_actions() -> Dict[str, Any]:
    """
    Look at saved goals + recent events and suggest next tasks to add & prioritize.
    Rules of thumb:
      - If 'lose' or 'weight' is in short goals and no health event in 7d -> suggest exercise task.
      - If 'friends'/'family' relationship goals and no social event in 10d -> suggest social reach-out.
      - If 'meditation' is a coping strategy and not scheduled in AM -> suggest AM 10m meditation.
      - If finance/invest appears in goals -> suggest 'invest VTI %salary' or review funds weekly.
    """
    db = _db()
    user = _ensure_user(db)
    groups = list_goals()
    short_text = " ".join([g["text"].lower() for g in groups["short"]])
    long_text = " ".join([g["text"].lower() for g in groups["long"]])
    advice: List[str] = []
    suggested_tasks: List[Dict[str, Any]] = []

    # Health cadence
    since_health = _days_since_last(db, user, KEYWORDS_HEALTH) or 999
    if (
        "lose" in short_text or "weight" in short_text or "health" in short_text
    ) and since_health > 7:
        advice.append(
            f"It’s been {since_health} days since a health activity; schedule a 30m workout."
        )
        suggested_tasks.append(
            {"title": "30m strength or 3-mile walk", "pillar": "Health", "impact": 5}
        )

    # Relationships cadence
    since_rel = _days_since_last(db, user, KEYWORDS_REL) or 999
    if (
        any(
            k in (short_text + " " + long_text)
            for k in ["friends", "family", "husband", "parents", "relationships"]
        )
        and since_rel > 10
    ):
        advice.append(
            f"No social time logged in {since_rel} days; message a friend and schedule dinner."
        )
        suggested_tasks.append(
            {
                "title": "Text a friend & set dinner",
                "pillar": "Relationships",
                "impact": 4,
            }
        )

    # Meditation / affirmations nudges
    if any("medit" in g["text"].lower() for g in groups["short"] + groups["long"]):
        advice.append(
            "Add 10m morning meditation + 2-line gratitude to stabilize mood."
        )
        suggested_tasks.append(
            {
                "title": "10m morning meditation + gratitude",
                "pillar": "Personal",
                "impact": 4,
            }
        )

    # Finance nudges
    if any(
        k in (short_text + " " + long_text)
        for k in ["invest", "finance", "house", "vti", "eb1", "immigration", "file"]
    ):
        advice.append(
            "Block 25m for finances: review VTI auto-invest %, set EB1 document task, and weekly money review."
        )
        suggested_tasks.append(
            {
                "title": "Finance block: review VTI %, EB1 docs",
                "pillar": "Money",
                "impact": 5,
            }
        )

    return {"advice": advice, "suggested_tasks": suggested_tasks}


@tool
def add_task(title: str, pillar: str | None = None, impact: int = 2) -> str:
    """Create a task in your to-do list."""
    db = _db()
    user = _ensure_user(db)
    db.add(Task(user_id=user.id, title=title, pillar=pillar, impact=int(impact)))
    db.commit()
    return f"Task added: {title}"


@tool
def list_today_events() -> List[Dict[str, Any]]:
    """Return today's events already synced from Google Calendar."""
    db = _db()
    user = _ensure_user(db)
    start, end = day_bounds(user.tz)
    evs = (
        db.query(Event)
        .filter(Event.user_id == user.id, Event.start >= start, Event.end <= end)
        .order_by(Event.start.asc())
        .all()
    )
    return [
        {
            "title": e.summary,
            "start": e.start.isoformat() if e.start else None,
            "end": e.end.isoformat() if e.end else None,
            "location": e.location,
        }
        for e in evs
    ]


@tool
async def plan_today() -> Dict[str, Any]:
    """Run the planner to produce an Eisenhower matrix and a timeboxed schedule."""
    db = _db()
    user = _ensure_user(db)
    start, end = day_bounds(user.tz)
    tasks = (
        db.query(Task)
        .filter(Task.user_id == user.id, Task.status == "open")
        .order_by(Task.impact.desc())
        .limit(50)
        .all()
    )
    goals = db.query(Goal).filter(Goal.user_id == user.id).all()
    stressors = db.query(Stressor).filter(Stressor.user_id == user.id).all()
    events = (
        db.query(Event)
        .filter(Event.user_id == user.id, Event.start >= start, Event.end <= end)
        .all()
    )

    context = {
        "identity": {"name": "You", "tz": user.tz},
        "tasks": [
            {
                "title": t.title,
                "pillar": t.pillar,
                "impact": t.impact,
                "dueAt": t.due_at.isoformat() if t.due_at else None,
            }
            for t in tasks
        ],
        "goals": [
            {
                "horizon": g.horizon,
                "text": g.text,
                "metric": g.metric,
                "target": g.target,
            }
            for g in goals
        ],
        "stressors": [
            {"trigger": s.trigger, "pattern": s.pattern, "coping": s.coping}
            for s in stressors
        ],
        "events": [
            {
                "title": e.summary,
                "start": e.start.isoformat() if e.start else None,
                "end": e.end.isoformat() if e.end else None,
                "location": e.location,
            }
            for e in events
        ],
    }
    payload = await call_claude(context)
    return {
        "eisenhower": payload.eisenhower.model_dump(),
        "schedule": [s.model_dump() for s in payload.schedule],
        "affirmations": payload.affirmations,
        "three_needles": payload.three_needles,
        "stress_guide": [r.model_dump() for r in payload.stress_guide],
        "nudges": payload.nudges,
    }


# ---------- Agent factory ----------
def build_agent(username: str = "Nidhi") -> Agent:
    if not settings.anthropic_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Chat requires an Anthropic key."
        )

    model = AnthropicModel(
        client_args={"api_key": settings.anthropic_key},
        model_id="claude-sonnet-4-20250514",
        max_tokens=1024,
        params={"temperature": 0.4},
    )

    system_prompt = (
        f"You are a caring personal assistant. The user's name is {username}. "
        "On first reply, greet by name and call goal_summary() to show known short/long-term goals. "
        "If none exist, ask concise questions to capture short goals (<=90d) and long goals (>=12m), "
        "then call upsert_goal() accordingly; confirm back to the user. "
        "Use list_today_events() to be context-aware. "
        "Proactively call suggest_next_actions() to nudge when cadence is off (health/social/finance/meditation). "
        "When the user asks to plan or prioritize, call plan_today() and present an Eisenhower matrix + 3 key 'needles'. "
        "Always format your entire reply in GitHub-Flavored Markdown. "
        "Prefer clear sections with headings (##), bullet lists, and tables when appropriate. "
        "For day plans, include sections exactly in this order: "
        "## Goals Summary, ## Today’s Events, ## 🎯 Top 3 Needles, ## 📌 Eisenhower Matrix (2x2 table), ## 🗓 Recommended Flow. "
        "Be concise and actionable."
    )

    return Agent(
        model=model,
        tools=[
            upsert_goal,
            list_goals,
            goal_summary,
            suggest_next_actions,
            add_task,
            list_today_events,
            plan_today,
        ],
        system_prompt=system_prompt,
    )
