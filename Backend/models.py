"""SQLAlchemy ORM models for the News Discovery & Management System."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def utcnow() -> datetime:
    """Naive UTC timestamp (SQLite-friendly)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    bookmarks: Mapped[list["Bookmark"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    articles: Mapped[list["Article"]] = relationship(back_populates="category")
    sources: Mapped[list["Source"]] = relationship(back_populates="category")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    url: Mapped[str | None] = mapped_column(String(500))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    description: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    language: Mapped[str] = mapped_column(String(10), default="en")
    country: Mapped[str] = mapped_column(String(10), default="us")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    category: Mapped["Category | None"] = relationship(back_populates="sources")
    articles: Mapped[list["Article"]] = relationship(back_populates="source")


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(300), index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(500))
    image_url: Mapped[str | None] = mapped_column(String(500))
    author: Mapped[str | None] = mapped_column(String(150))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    published_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_breaking: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    ai_summary: Mapped[str | None] = mapped_column(Text)  # cached Gemini summary
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    source: Mapped["Source | None"] = relationship(back_populates="articles")
    category: Mapped["Category | None"] = relationship(back_populates="articles")
    bookmarks: Mapped[list["Bookmark"]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )


class Bookmark(Base):
    __tablename__ = "bookmarks"
    __table_args__ = (UniqueConstraint("user_id", "article_id", name="uq_bookmark_user_article"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped["User"] = relationship(back_populates="bookmarks")
    article: Mapped["Article"] = relationship(back_populates="bookmarks")


class DiscoveryRun(Base):
    """Log of each third-party discovery run (manual, search, or scheduled)."""

    __tablename__ = "discovery_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    trigger: Mapped[str] = mapped_column(String(20), default="manual")  # manual|auto|search
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running|success|error
    error_code: Mapped[str | None] = mapped_column(String(20))  # config|rate_limited|provider|unexpected
    imported: Mapped[int] = mapped_column(Integer, default=0)
    skipped: Mapped[int] = mapped_column(Integer, default=0)
    categories: Mapped[str] = mapped_column(Text, default="")  # comma-separated slugs
    message: Mapped[str | None] = mapped_column(Text)
