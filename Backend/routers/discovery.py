"""Discovery endpoints: live third-party fetching, search, run history, and trending."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from auth import get_current_user
from config import get_settings
from database import get_db
from models import Article, DiscoveryRun, User, utcnow
from schemas import ArticleOut, DiscoveryRunOut, DiscoveryStatus
from services.news_fetcher import NEWSAPI_CATEGORIES, run_discovery, run_news_search

router = APIRouter(prefix="/discovery", tags=["discovery"])

# Map a failed run's error_code to the appropriate HTTP status.
_ERROR_STATUS = {
    "config": status.HTTP_400_BAD_REQUEST,
    "rate_limited": status.HTTP_429_TOO_MANY_REQUESTS,
    "provider": status.HTTP_502_BAD_GATEWAY,
    "unexpected": status.HTTP_502_BAD_GATEWAY,
}


def _raise_run_error(run: DiscoveryRun) -> None:
    """Turn a failed DiscoveryRun into an HTTPException with a fitting status code."""
    raise HTTPException(
        status_code=_ERROR_STATUS.get(run.error_code or "provider", status.HTTP_502_BAD_GATEWAY),
        detail=run.message or "Discovery failed",
    )


@router.get("/trending", response_model=list[ArticleOut])
def trending(
    db: Session = Depends(get_db),
    limit: int = Query(default=10, ge=1, le=50),
    days: int = Query(default=7, ge=1, le=90),
) -> list[Article]:
    """Most-viewed articles published within the last `days` days."""
    cutoff = utcnow() - timedelta(days=days)
    return (
        db.query(Article)
        .filter(Article.published_at >= cutoff)
        .order_by(Article.views.desc(), Article.published_at.desc())
        .limit(limit)
        .all()
    )


@router.post("/fetch", response_model=DiscoveryRunOut)
def fetch_live_news(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    category: str | None = Query(default=None),
    country: str = Query(default="us", min_length=2, max_length=2),
    page_size: int = Query(default=20, ge=1, le=100),
) -> DiscoveryRun:
    """Fetch live top headlines from the configured news provider (auth required).

    New articles are stored; duplicates (matched by URL) are skipped. The outcome
    is recorded in the discovery run history — see ``GET /api/discovery/runs``.
    """
    if category and category not in NEWSAPI_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported category '{category}'. Supported: {', '.join(NEWSAPI_CATEGORIES)}",
        )
    run = run_discovery(
        db, trigger="manual", category=category, country=country, page_size=page_size
    )
    if run.status == "error":
        _raise_run_error(run)
    return run


@router.post("/search", response_model=DiscoveryRunOut)
def search_live_news(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    q: str = Query(min_length=2, max_length=100),
    language: str = Query(default="en", min_length=2, max_length=5),
    page_size: int = Query(default=20, ge=1, le=100),
    from_date: date | None = Query(
        default=None, description="Only results published on/after this date (YYYY-MM-DD)"
    ),
    to_date: date | None = Query(
        default=None, description="Only results published on/before this date (YYYY-MM-DD)"
    ),
) -> DiscoveryRun:
    """Search the provider for articles matching a keyword (auth required).

    Optional ``from_date`` / ``to_date`` narrow the publication window so
    archived (past) stories can be pulled in.
    """
    run = run_news_search(
        db,
        query=q,
        language=language,
        page_size=page_size,
        from_date=from_date.isoformat() if from_date else None,
        to_date=to_date.isoformat() if to_date else None,
    )
    if run.status == "error":
        _raise_run_error(run)
    return run


@router.get("/runs", response_model=list[DiscoveryRunOut])
def list_runs(
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[DiscoveryRun]:
    """Recent discovery run history, newest first."""
    return (
        db.query(DiscoveryRun)
        .order_by(DiscoveryRun.started_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/status", response_model=DiscoveryStatus)
def discovery_status(db: Session = Depends(get_db)) -> DiscoveryStatus:
    """Integration status: whether a key is configured and when the last run happened."""
    settings = get_settings()
    last_run = (
        db.query(DiscoveryRun)
        .order_by(DiscoveryRun.started_at.desc())
        .first()
    )
    return DiscoveryStatus(
        configured=bool(settings.NEWS_API_KEY),
        provider="NewsAPI.org",
        auto_fetch_enabled=settings.NEWS_AUTO_FETCH,
        fetch_interval_minutes=settings.NEWS_FETCH_INTERVAL_MINUTES,
        last_run=DiscoveryRunOut.model_validate(last_run) if last_run else None,
    )
