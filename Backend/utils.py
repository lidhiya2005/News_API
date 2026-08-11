"""Small shared helpers used across routers."""
import re
import unicodedata
from math import ceil

from sqlalchemy.orm import Query, Session

from schemas import Page


def slugify(value: str) -> str:
    """Convert a string into a URL-friendly slug."""
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[-\s]+", "-", value)
    return value or "item"


def unique_slug(db: Session, model, title: str) -> str:
    """Build a unique slug for a given model by appending a numeric suffix on collision."""
    base = slugify(title)
    candidate = base
    counter = 2
    while db.query(model).filter(model.slug == candidate).first() is not None:
        candidate = f"{base}-{counter}"
        counter += 1
    return candidate


def paginate(query: Query, page: int, size: int) -> Page:
    """Apply offset/limit to a query and wrap the result in a Page envelope."""
    page = max(1, page)
    size = min(max(1, size), 100)
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    pages = ceil(total / size) if total else 0
    return Page(items=items, total=total, page=page, size=size, pages=pages)
