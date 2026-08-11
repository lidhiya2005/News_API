"""Article endpoints: discovery (list/search/filter), detail, and management CRUD."""
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Article, Category, Source, User, utcnow
from schemas import ArticleCreate, ArticleOut, ArticleUpdate, Page
from utils import paginate, unique_slug

router = APIRouter(prefix="/articles", tags=["articles"])


def _resolve_category(db: Session, value: str | int | None) -> Category | None:
    """Resolve a category from either its numeric id or its slug."""
    if value is None:
        return None
    if isinstance(value, int):
        return db.get(Category, value)
    if value.isdigit():
        return db.get(Category, int(value))
    return db.query(Category).filter(Category.slug == value).first()


@router.get("", response_model=Page[ArticleOut])
def list_articles(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, description="Full-text search on title/summary/content"),
    category: str | int | None = Query(default=None, description="Category id or slug"),
    source_id: int | None = Query(default=None),
    featured: bool | None = Query(default=None),
    breaking: bool | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    sort: str = Query(default="newest", pattern="^(newest|oldest|popular|title)$"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> Page[ArticleOut]:
    """List articles with search, filtering, sorting, and pagination."""
    query = db.query(Article)

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(Article.title.ilike(like), Article.summary.ilike(like), Article.content.ilike(like))
        )

    cat = _resolve_category(db, category)
    if category is not None and cat is None:
        raise HTTPException(status_code=404, detail="Category not found")
    if cat is not None:
        query = query.filter(Article.category_id == cat.id)

    if source_id is not None:
        query = query.filter(Article.source_id == source_id)
    if featured is not None:
        query = query.filter(Article.is_featured == featured)
    if breaking is not None:
        query = query.filter(Article.is_breaking == breaking)
    if from_date:
        query = query.filter(Article.published_at >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        query = query.filter(Article.published_at <= datetime.combine(to_date, datetime.max.time()))

    if sort == "oldest":
        query = query.order_by(Article.published_at.asc())
    elif sort == "popular":
        query = query.order_by(Article.views.desc(), Article.published_at.desc())
    elif sort == "title":
        query = query.order_by(Article.title.asc())
    else:
        query = query.order_by(Article.published_at.desc())

    return paginate(query, page, size)


@router.get("/{article_id}", response_model=ArticleOut)
def get_article(article_id: int, db: Session = Depends(get_db)) -> Article:
    """Fetch a single article and increment its view counter."""
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    article.views += 1
    db.commit()
    db.refresh(article)
    return article


@router.post("", response_model=ArticleOut, status_code=status.HTTP_201_CREATED)
def create_article(
    payload: ArticleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Article:
    """Create a new article (authenticated users only)."""
    if payload.category_id is not None and db.get(Category, payload.category_id) is None:
        raise HTTPException(status_code=400, detail="Invalid category_id")
    if payload.source_id is not None and db.get(Source, payload.source_id) is None:
        raise HTTPException(status_code=400, detail="Invalid source_id")

    article = Article(
        **payload.model_dump(),
        slug=unique_slug(db, Article, payload.title),
    )
    if article.published_at is None:
        article.published_at = utcnow()

    db.add(article)
    db.commit()
    db.refresh(article)
    return article


@router.put("/{article_id}", response_model=ArticleOut)
def update_article(
    article_id: int,
    payload: ArticleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Article:
    """Update an article (authenticated users only)."""
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    if payload.category_id is not None and db.get(Category, payload.category_id) is None:
        raise HTTPException(status_code=400, detail="Invalid category_id")
    if payload.source_id is not None and db.get(Source, payload.source_id) is None:
        raise HTTPException(status_code=400, detail="Invalid source_id")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(article, field, value)

    db.commit()
    db.refresh(article)
    return article


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(
    article_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    """Delete an article (authenticated users only)."""
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    db.delete(article)
    db.commit()
