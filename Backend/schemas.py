"""Pydantic schemas (request/response models) for the API."""
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

T = TypeVar("T")


# --------------------------------------------------------------------------
# Generic pagination envelope
# --------------------------------------------------------------------------
class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int


# --------------------------------------------------------------------------
# Auth / users
# --------------------------------------------------------------------------
class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    full_name: str | None = Field(default=None, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    username: str
    full_name: str | None
    is_superuser: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# --------------------------------------------------------------------------
# Categories
# --------------------------------------------------------------------------
class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: str | None
    created_at: datetime


# --------------------------------------------------------------------------
# Sources
# --------------------------------------------------------------------------
class SourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    url: str | None = None
    category_id: int | None = None
    description: str | None = None
    logo_url: str | None = None
    language: str = "en"
    country: str = "us"


class SourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    url: str | None = None
    category_id: int | None = None
    description: str | None = None
    logo_url: str | None = None
    language: str | None = None
    country: str | None = None
    is_active: bool | None = None


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    url: str | None
    category_id: int | None
    category: CategoryOut | None
    description: str | None
    logo_url: str | None
    language: str
    country: str
    is_active: bool
    created_at: datetime


# --------------------------------------------------------------------------
# Articles
# --------------------------------------------------------------------------
class ArticleCreate(BaseModel):
    title: str = Field(min_length=5, max_length=300)
    summary: str | None = None
    content: str | None = None
    url: str | None = None
    image_url: str | None = None
    author: str | None = Field(default=None, max_length=150)
    source_id: int | None = None
    category_id: int | None = None
    published_at: datetime | None = None
    is_featured: bool = False
    is_breaking: bool = False


class ArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=300)
    summary: str | None = None
    content: str | None = None
    url: str | None = None
    image_url: str | None = None
    author: str | None = Field(default=None, max_length=150)
    source_id: int | None = None
    category_id: int | None = None
    published_at: datetime | None = None
    is_featured: bool | None = None
    is_breaking: bool | None = None


class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    summary: str | None
    content: str | None
    url: str | None
    image_url: str | None
    author: str | None
    source_id: int | None
    source: SourceOut | None
    category_id: int | None
    category: CategoryOut | None
    published_at: datetime
    is_featured: bool
    is_breaking: bool
    views: int
    created_at: datetime


# --------------------------------------------------------------------------
# Bookmarks
# --------------------------------------------------------------------------
class BookmarkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    article: ArticleOut
    created_at: datetime


# --------------------------------------------------------------------------
# Discovery (third-party news API integration)
# --------------------------------------------------------------------------
class DiscoveryRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trigger: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    error_code: str | None
    imported: int
    skipped: int
    categories: list[str]
    message: str | None

    @field_validator("categories", mode="before")
    @classmethod
    def _split_categories(cls, value):
        if isinstance(value, str):
            return [c for c in value.split(",") if c]
        return value


class DiscoveryStatus(BaseModel):
    configured: bool
    provider: str
    auto_fetch_enabled: bool
    fetch_interval_minutes: int
    last_run: DiscoveryRunOut | None
