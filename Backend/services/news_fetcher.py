"""Third-party news discovery service (NewsAPI.org).

Provides:
- ``fetch_top_headlines`` / ``search_news`` — low-level provider calls.
- ``run_discovery`` / ``run_news_search`` — wrapped in a persisted DiscoveryRun log.
- ``run_auto_discovery`` — loops over configured categories for the scheduler.

All calls require ``NEWS_API_KEY`` to be set in ``Backend/.env``.
"""
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from config import get_settings
from database import SessionLocal
from models import Article, Category, DiscoveryRun, Source, utcnow
from utils import unique_slug


class NewsApiError(Exception):
    """Base error for provider issues."""


class NewsApiNotConfiguredError(NewsApiError):
    """Raised when a fetch is attempted without a NEWS_API_KEY."""


class NewsApiRateLimitedError(NewsApiError):
    """Raised when the provider rate limit (quota) is hit."""


# NewsAPI topic names that map onto our seeded category slugs.
NEWSAPI_CATEGORIES = (
    "business",
    "entertainment",
    "general",
    "health",
    "science",
    "sports",
    "technology",
)


# --------------------------------------------------------------------------
# Low-level provider helpers
# --------------------------------------------------------------------------
def _fetch_json(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    """GET ``endpoint`` with ``params`` and return parsed JSON, raising on errors."""
    settings = get_settings()
    if not settings.NEWS_API_KEY:
        raise NewsApiNotConfiguredError(
            "NEWS_API_KEY is not set. Add it to Backend/.env to enable live discovery."
        )

    params = {**params, "apiKey": settings.NEWS_API_KEY}
    url = f"{settings.NEWS_API_BASE_URL.rstrip('/')}/{endpoint}"

    try:
        response = httpx.get(url, params=params, timeout=30)
    except httpx.HTTPError as exc:
        raise NewsApiError(f"Network error talking to the news provider: {exc}") from exc

    if response.status_code == 429:
        raise NewsApiRateLimitedError(
            "News provider rate limit reached (NewsAPI.org free tier: 100 requests/day). "
            "Try again later or add a key with a higher quota."
        )

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:200] if exc.response else ""
        raise NewsApiError(
            f"Provider returned HTTP {response.status_code}" + (f": {detail}" if detail else "")
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise NewsApiError(
            f"Provider returned an unreadable response (not valid JSON): {response.text[:100]}"
        ) from exc

    if isinstance(payload, dict) and payload.get("status") == "error":
        code = payload.get("code", "unknown")
        message = payload.get("message", "Unknown provider error")
        if code == "rateLimited":
            raise NewsApiRateLimitedError(message)
        raise NewsApiError(f"Provider error ({code}): {message}")
    return payload


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return utcnow()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None)
    except ValueError:
        return utcnow()


def _ensure_source(db: Session, name: str, url: str | None) -> Source | None:
    if not name:
        return None
    source = db.query(Source).filter(Source.name == name).first()
    if source:
        return source
    source = Source(name=name, slug=unique_slug(db, Source, name), url=url or None)
    db.add(source)
    db.flush()
    return source


def _ensure_category(db: Session, slug: str) -> Category | None:
    category = db.query(Category).filter(Category.slug == slug).first()
    if category:
        return category
    # NewsAPI uses "general" as a topic — fall back to our "World" category.
    if slug == "general":
        return db.query(Category).filter(Category.slug == "world").first()
    return None


def _store_articles(db: Session, items: list[dict], category_slug: str | None = None) -> tuple[int, int]:
    """Insert provider articles, deduplicating by URL. Returns (imported, skipped)."""
    imported = 0
    skipped = 0
    cat = _ensure_category(db, category_slug) if category_slug else None

    for item in items:
        url = item.get("url")
        title = item.get("title")
        if not url or not title:
            skipped += 1
            continue

        if db.query(Article).filter(Article.url == url).first():
            skipped += 1
            continue

        source = _ensure_source(db, (item.get("source") or {}).get("name", ""), url)
        db.add(
            Article(
                title=title,
                slug=unique_slug(db, Article, title),
                summary=item.get("description"),
                content=item.get("content"),
                url=url,
                image_url=item.get("urlToImage"),
                author=item.get("author"),
                source=source,
                category=cat,
                published_at=_parse_datetime(item.get("publishedAt")),
            )
        )
        imported += 1

    db.commit()
    return imported, skipped


# --------------------------------------------------------------------------
# Provider calls
# --------------------------------------------------------------------------
def fetch_top_headlines(
    db: Session,
    *,
    category: str | None = None,
    country: str = "us",
    page_size: int = 20,
) -> dict:
    """Pull top headlines from the provider and store new articles."""
    if category and category not in NEWSAPI_CATEGORIES:
        raise NewsApiError(
            f"Unsupported category '{category}'. Supported: {', '.join(NEWSAPI_CATEGORIES)}"
        )

    params = {"country": country, "pageSize": min(max(1, page_size), 100)}
    if category:
        params["category"] = category

    payload = _fetch_json("top-headlines", params)
    imported, skipped = _store_articles(db, payload.get("articles", []), category or "general")
    return {"imported": imported, "skipped": skipped, "categories": [category or "general"]}


def search_news(
    db: Session,
    *,
    query: str,
    language: str = "en",
    page_size: int = 20,
    from_date: str | None = None,
    to_date: str | None = None,
) -> dict:
    """Search news for a keyword and store new articles.

    ``from_date`` / ``to_date`` (ISO ``YYYY-MM-DD``) restrict results to a
    publication window, letting callers pull archived (past) stories.
    """
    params = {
        "q": query,
        "language": language,
        "sortBy": "publishedAt",
        "pageSize": min(max(1, page_size), 100),
    }
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    payload = _fetch_json("everything", params)
    imported, skipped = _store_articles(db, payload.get("articles", []))
    return {"imported": imported, "skipped": skipped, "categories": []}


# --------------------------------------------------------------------------
# Run wrappers (persisted DiscoveryRun rows)
# --------------------------------------------------------------------------
def _error_code(exc: Exception) -> str:
    """Classify an exception into a stable machine-readable code."""
    if isinstance(exc, NewsApiNotConfiguredError):
        return "config"
    if isinstance(exc, NewsApiRateLimitedError):
        return "rate_limited"
    if isinstance(exc, NewsApiError):
        return "provider"
    return "unexpected"


def _fail_run(run: DiscoveryRun, db: Session, exc: Exception) -> DiscoveryRun:
    """Record a failed run and reset any broken transaction state."""
    db.rollback()
    return _finish_run(
        run,
        db,
        status="error",
        error_code=_error_code(exc),
        message=str(exc),
    )


def _finish_run(run: DiscoveryRun, db: Session, **kwargs) -> DiscoveryRun:
    for key, value in kwargs.items():
        setattr(run, key, value)
    run.finished_at = utcnow()
    db.commit()
    db.refresh(run)
    return run


def run_discovery(
    db: Session,
    *,
    trigger: str = "manual",
    category: str | None = None,
    country: str = "us",
    page_size: int = 20,
) -> DiscoveryRun:
    """Fetch top headlines and record the outcome in a DiscoveryRun row."""
    run = DiscoveryRun(trigger=trigger)
    db.add(run)
    db.commit()
    db.refresh(run)
    try:
        result = fetch_top_headlines(db, category=category, country=country, page_size=page_size)
    except Exception as exc:
        return _fail_run(run, db, exc)
    return _finish_run(
        run,
        db,
        status="success",
        imported=result["imported"],
        skipped=result["skipped"],
        categories=",".join(result["categories"]),
        message=f"Imported {result['imported']} article(s) from top headlines",
    )


def run_news_search(
    db: Session,
    *,
    query: str,
    language: str = "en",
    page_size: int = 20,
    from_date: str | None = None,
    to_date: str | None = None,
) -> DiscoveryRun:
    """Search the provider and record the outcome in a DiscoveryRun row."""
    run = DiscoveryRun(trigger="search")
    db.add(run)
    db.commit()
    db.refresh(run)
    try:
        result = search_news(
            db,
            query=query,
            language=language,
            page_size=page_size,
            from_date=from_date,
            to_date=to_date,
        )
    except Exception as exc:
        return _fail_run(run, db, exc)
    return _finish_run(
        run,
        db,
        status="success",
        imported=result["imported"],
        skipped=result["skipped"],
        categories=",".join(result["categories"]),
        message=f"Imported {result['imported']} article(s) for query '{query}'",
    )


def run_auto_discovery() -> DiscoveryRun:
    """Fetch one page of headlines per configured category. Opens its own session."""
    settings = get_settings()
    db = SessionLocal()
    try:
        run = DiscoveryRun(trigger="auto")
        db.add(run)
        db.commit()
        db.refresh(run)

        imported_total = 0
        skipped_total = 0
        categories_fetched = []
        try:
            for slug in settings.NEWS_AUTO_CATEGORIES:
                try:
                    result = fetch_top_headlines(
                        db, category=slug, country=settings.NEWS_COUNTRY, page_size=20
                    )
                    imported_total += result["imported"]
                    skipped_total += result["skipped"]
                    categories_fetched.append(slug)
                except NewsApiRateLimitedError:
                    # Stop early — further requests would fail the same way.
                    db.rollback()
                    break
                except Exception:
                    # A single failing category shouldn't poison the session for the rest.
                    db.rollback()
                    continue
            return _finish_run(
                run,
                db,
                status="success",
                imported=imported_total,
                skipped=skipped_total,
                categories=",".join(categories_fetched),
                message=f"Scheduled fetch imported {imported_total} article(s)",
            )
        except Exception as exc:  # unexpected errors still get logged
            return _fail_run(run, db, exc)
    finally:
        db.close()
