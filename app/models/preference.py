from sqlalchemy import String, Float, ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.base import Base
from .common import gen_id, now_utc

class Preference(Base):
    __tablename__ = "preference"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"))
    key: Mapped[str] = mapped_column(String)
    value: Mapped[dict | str | int | float | bool | None] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
