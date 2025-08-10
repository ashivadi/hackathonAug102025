from sqlalchemy import String, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.base import Base
from .common import gen_id, now_utc

class Plan(Base):
    __tablename__ = "plan"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"))
    date: Mapped[datetime] = mapped_column(DateTime, default=now_utc)  # normalize to day start in prod
    matrix: Mapped[dict] = mapped_column(JSON)
    schedule: Mapped[list] = mapped_column(JSON)
    affirmations: Mapped[dict] = mapped_column(JSON)
    needles: Mapped[dict] = mapped_column(JSON)
    stress_guide: Mapped[list] = mapped_column(JSON)
    nudges: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_plan_user_date"),)
