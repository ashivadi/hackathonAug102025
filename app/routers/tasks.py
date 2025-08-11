from __future__ import annotations
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.user import User
from app.models.task import Task
from app.core.config import settings

router = APIRouter(tags=["tasks"])
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


@router.get("/tasks", response_class=HTMLResponse)
def tasks_page(request: Request, db: Session = Depends(get_db)):
    ensure_user(db)
    tasks = db.query(Task).order_by(Task.status.asc(), Task.impact.desc()).all()
    return templates.TemplateResponse(
        "tasks.html", {"request": request, "tasks": tasks}
    )


@router.get("/v1/tasks/fragment", response_class=HTMLResponse)
def tasks_fragment(request: Request, db: Session = Depends(get_db)):
    ensure_user(db)
    tasks = db.query(Task).order_by(Task.status.asc(), Task.impact.desc()).all()
    return templates.TemplateResponse(
        "_tasks_table.html", {"request": request, "tasks": tasks}
    )


class TaskIn(BaseModel):
    title: str
    pillar: Optional[str] = None
    impact: int = 3
    dueAt: Optional[str] = None


@router.post("/v1/tasks", response_class=HTMLResponse)
def create_task(req: TaskIn, request: Request, db: Session = Depends(get_db)):
    user = ensure_user(db)
    due = None
    if req.dueAt:
        try:
            due = datetime.fromisoformat(req.dueAt.replace("Z", ""))
        except Exception:
            due = None
    db.add(
        Task(
            user_id=user.id,
            title=req.title,
            pillar=req.pillar,
            impact=int(req.impact),
            due_at=due,
        )
    )
    db.commit()
    return tasks_fragment(request, db)


class TaskPatch(BaseModel):
    title: Optional[str] = None
    pillar: Optional[str] = None
    impact: Optional[int] = None
    dueAt: Optional[str] = None


@router.patch("/v1/tasks/{task_id}", response_class=HTMLResponse)
def update_task(
    task_id: int, req: TaskPatch, request: Request, db: Session = Depends(get_db)
):
    ensure_user(db)
    t = db.get(Task, task_id)
    if not t:
        return tasks_fragment(request, db)
    if req.title is not None:
        t.title = req.title
    if req.pillar is not None:
        t.pillar = req.pillar
    if req.impact is not None:
        t.impact = int(req.impact)
    if req.dueAt is not None:
        try:
            t.due_at = (
                datetime.fromisoformat(req.dueAt.replace("Z", ""))
                if req.dueAt
                else None
            )
        except Exception:
            t.due_at = None
    db.commit()
    return tasks_fragment(request, db)


@router.post("/v1/tasks/{task_id}/toggle", response_class=HTMLResponse)
def toggle_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    ensure_user(db)
    t = db.get(Task, task_id)
    if t:
        t.status = "done" if t.status != "done" else "open"
        db.commit()
    return tasks_fragment(request, db)


@router.delete("/v1/tasks/{task_id}", response_class=HTMLResponse)
def delete_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    ensure_user(db)
    t = db.get(Task, task_id)
    if t:
        db.delete(t)
        db.commit()
    return tasks_fragment(request, db)
