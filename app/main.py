from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.core.config import settings
from app.core.time import day_bounds

# --- Import all models so create_all sees them ---
from app.models import (
    user,
    task,
    goal,
    stressor,
    preference,
    trait,
    plan,
    message,
    calendar_account,
    event,
)
from app.models.user import User
from app.models.plan import Plan

# --- Routers ---
from app.routers import (
    plan as plan_router,
    memory as memory_router,
    inbox as inbox_router,
    invite as invite_router,
    chat as chat_router,
    goals as goals_router,
    google_auth as google_auth_router,
    calendar as calendar_router,
)

# Create tables (SQLite)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Personal Assistant (FastAPI)")

# Register routers (order doesn't really matter)
app.include_router(plan_router.router)
app.include_router(memory_router.router)
app.include_router(inbox_router.router)
app.include_router(invite_router.router)
app.include_router(chat_router.router)
app.include_router(goals_router.router)
app.include_router(google_auth_router.router)
app.include_router(calendar_router.router)

templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Home dashboard: shows today's plan (Eisenhower, schedule, etc.)."""
    db: Session = SessionLocal()
    try:
        user_row = db.query(User).first()
        plan_row = None
        if user_row:
            start, end = day_bounds(user_row.tz)
            plan_row = (
                db.query(Plan)
                .filter(
                    Plan.user_id == user_row.id, Plan.date >= start, Plan.date <= end
                )
                .one_or_none()
            )
        return templates.TemplateResponse(
            "index.html", {"request": request, "plan": plan_row}
        )
    finally:
        db.close()


@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """Simple chat UI for the assistant."""
    return templates.TemplateResponse("chat.html", {"request": request})


# ---------------- Scheduler: daily 07:00 in DEFAULT_TZ ----------------
scheduler = AsyncIOScheduler()


async def daily_job():
    """Triggers the day planner; same as clicking 'Run Today’s Plan'."""
    import httpx

    async with httpx.AsyncClient() as client:
        await client.post("http://127.0.0.1:8000/v1/plan/run")


@app.on_event("startup")
def on_start():
    if settings.enable_scheduler:
        scheduler.add_job(
            daily_job, CronTrigger(hour=7, minute=0, timezone=settings.default_tz)
        )
        scheduler.start()


# Optional: quick sanity route for Google creds (remove in prod)
# @app.get("/debug/google")
# def debug_google():
#     import os
#     cid = os.getenv("GOOGLE_CLIENT_ID", "")
#     redir = os.getenv("GOOGLE_REDIRECT_URI", "")
#     return {
#         "client_id_present": bool(cid),
#         "client_id_preview": (cid[:8] + "…") if cid else "",
#         "redirect_uri": redir,
#     }
