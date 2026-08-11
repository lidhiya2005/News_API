"""Bookmark endpoints — save articles to read later (per user)."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Article, Bookmark, User
from schemas import BookmarkOut, Page
from utils import paginate

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


@router.get("", response_model=Page[BookmarkOut])
def list_bookmarks(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> Page[BookmarkOut]:
    """List the current user's bookmarks, newest first."""
    query = (
        db.query(Bookmark)
        .filter(Bookmark.user_id == user.id)
        .order_by(Bookmark.created_at.desc())
    )
    return paginate(query, page, size)


@router.post("/{article_id}", response_model=BookmarkOut, status_code=status.HTTP_201_CREATED)
def add_bookmark(
    article_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Bookmark:
    """Bookmark an article for the current user."""
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    existing = (
        db.query(Bookmark)
        .filter(Bookmark.user_id == user.id, Bookmark.article_id == article_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Article already bookmarked")

    bookmark = Bookmark(user_id=user.id, article_id=article_id)
    db.add(bookmark)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Article already bookmarked")
    db.refresh(bookmark)
    return bookmark


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_bookmark(
    article_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Remove a bookmark for the current user."""
    bookmark = (
        db.query(Bookmark)
        .filter(Bookmark.user_id == user.id, Bookmark.article_id == article_id)
        .first()
    )
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    db.delete(bookmark)
    db.commit()
