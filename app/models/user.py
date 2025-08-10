from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.base import Base
from .common import gen_id, now_utc

class User(Base):
    __tablename__ = "user"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    email: Mapped[str] = mapped_column(String, unique=True)
    tz: Mapped[str] = mapped_column(String, default="America/Los_Angeles")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
