"""News source endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Article, Category, Source, User
from schemas import SourceCreate, SourceOut, SourceUpdate
from utils import unique_slug

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceOut])
def list_sources(
    db: Session = Depends(get_db),
    category_id: int | None = Query(default=None),
    active_only: bool = Query(default=True),
) -> list[Source]:
    """List all news sources, optionally filtered by category."""
    query = db.query(Source)
    if category_id is not None:
        query = query.filter(Source.category_id == category_id)
    if active_only:
        query = query.filter(Source.is_active.is_(True))
    return query.order_by(Source.name.asc()).all()


@router.post("", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
def create_source(
    payload: SourceCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Source:
    """Create a new news source (authenticated users only)."""
    if db.query(Source).filter(Source.name == payload.name).first():
        raise HTTPException(status_code=409, detail="Source already exists")
    if payload.category_id is not None and db.get(Category, payload.category_id) is None:
        raise HTTPException(status_code=400, detail="Invalid category_id")

    source = Source(**payload.model_dump(), slug=unique_slug(db, Source, payload.name))
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.put("/{source_id}", response_model=SourceOut)
def update_source(
    source_id: int,
    payload: SourceUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Source:
    """Update a news source (authenticated users only)."""
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    if payload.category_id is not None and db.get(Category, payload.category_id) is None:
        raise HTTPException(status_code=400, detail="Invalid category_id")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(source, field, value)

    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(
    source_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    """Delete a news source (authenticated users only)."""
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    db.query(Article).filter(Article.source_id == source.id).update({Article.source_id: None})
    db.delete(source)
    db.commit()
