from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tiny.db import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Site(db.Model):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    custom_css: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    pages: Mapped[list["Page"]] = relationship(
        back_populates="site",
        cascade="all, delete-orphan",
        order_by="Page.id",
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="site",
        cascade="all, delete-orphan",
        order_by="ChatMessage.id",
    )


class Page(db.Model):
    __tablename__ = "pages"
    __table_args__ = (UniqueConstraint("site_id", "slug", name="uq_pages_site_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False, default="")
    layout: Mapped[str] = mapped_column(String(16), nullable=False, default="page")
    is_post: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)

    site: Mapped[Site] = relationship(back_populates="pages")


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    site: Mapped[Site] = relationship(back_populates="chat_messages")
