from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.base import Base
from .common import gen_id, now_utc

class Goal(Base):
    __tablename__ = "goal"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"))
    horizon: Mapped[str] = mapped_column(String)  # 14d|90d|12m
    text: Mapped[str] = mapped_column(String)
    metric: Mapped[str | None] = mapped_column(String, nullable=True)
    target: Mapped[float | None]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
