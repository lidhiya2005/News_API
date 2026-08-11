"""News Discovery & Management System — FastAPI backend entry point."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from config import get_settings
from database import Base, engine
from routers import articles, auth, bookmarks, categories, discovery, sources
from seed import seed_database
from services.news_fetcher import run_auto_discovery

settings = get_settings()
logger = logging.getLogger("uvicorn.error")


def _apply_lightweight_migrations() -> None:
    """Add columns that were introduced after a dev database was first created."""
    inspector = inspect(engine)
    if "discovery_runs" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("discovery_runs")}
    if "error_code" not in existing:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE discovery_runs ADD COLUMN error_code VARCHAR(20)"))
        logger.info("[migration] added discovery_runs.error_code")


async def _auto_discovery_loop() -> None:
    """Periodically fetch news from the configured provider (opt-in)."""
    interval = settings.NEWS_FETCH_INTERVAL_MINUTES * 60
    logger.info(
        "[discovery] auto-fetch enabled — running every %s minute(s)",
        settings.NEWS_FETCH_INTERVAL_MINUTES,
    )
    while True:
        await asyncio.sleep(interval)
        try:
            run = await asyncio.to_thread(run_auto_discovery)
            logger.info(
                "[discovery] auto-fetch finished (status=%s, imported=%s)",
                run.status,
                run.imported,
            )
        except Exception as exc:  # never let the loop die
            logger.error("[discovery] auto-fetch failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables, seed demo data, and start the optional discovery scheduler."""
    Base.metadata.create_all(bind=engine)
    _apply_lightweight_migrations()
    if settings.SEED_ON_STARTUP:
        created = seed_database()
        if sum(created.values()):
            print(f"[seed] Created: {created}")

    scheduler = None
    if settings.NEWS_API_KEY and settings.NEWS_AUTO_FETCH:
        scheduler = asyncio.create_task(_auto_discovery_loop())

    yield

    if scheduler:
        scheduler.cancel()
        await asyncio.gather(scheduler, return_exceptions=True)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "REST API for discovering, managing, and curating news articles. "
        "Interactive docs at /docs."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_PREFIX, tags=["auth"])
app.include_router(articles.router, prefix=settings.API_PREFIX)
app.include_router(categories.router, prefix=settings.API_PREFIX)
app.include_router(sources.router, prefix=settings.API_PREFIX)
app.include_router(bookmarks.router, prefix=settings.API_PREFIX)
app.include_router(discovery.router, prefix=settings.API_PREFIX)


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/api/health",
        "message": "News Discovery & Management API is running",
    }


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "version": settings.APP_VERSION}


# Inline SVG favicon so browsers don't log a 404 for /favicon.ico.
_FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<rect width="64" height="64" rx="14" fill="#2563eb"/>'
    '<text x="32" y="45" font-family="Arial, Helvetica, sans-serif" '
    'font-size="38" font-weight="bold" fill="#ffffff" '
    'text-anchor="middle">N</text></svg>'
)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    """Serve an SVG favicon to keep browser requests from 404ing."""
    return Response(content=_FAVICON_SVG, media_type="image/svg+xml")
