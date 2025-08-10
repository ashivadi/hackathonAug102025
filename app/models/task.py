from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.base import Base
from .common import gen_id, now_utc

class Task(Base):
    __tablename__ = "task"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"))
    title: Mapped[str] = mapped_column(String)
    pillar: Mapped[str | None] = mapped_column(String, nullable=True)  # Money|Health|Relationships|Work|Personal
    impact: Mapped[int] = mapped_column(Integer, default=1)            # 1..5
    due_at: Mapped[datetime | None]
    source: Mapped[str] = mapped_column(String, default="manual")
    status: Mapped[str] = mapped_column(String, default="open")        # open|done|blocked
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
