from sqlalchemy import String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.db.base import Base
from .common import gen_id, now_utc

class Message(Base):
    __tablename__ = "message"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("user.id"))
    ts: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    channel: Mapped[str] = mapped_column(String)  # email|slack|telegram
    from_addr: Mapped[str | None] = mapped_column(String, nullable=True)
    subject: Mapped[str | None] = mapped_column(String, nullable=True)
    body_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    intent: Mapped[str] = mapped_column(String, default="fyi")  # invite|task|fyi
    data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
