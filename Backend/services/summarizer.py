"""AI article summarization via Google Gemini (google-genai SDK)."""
import ipaddress
import logging
import re
import socket
from dataclasses import dataclass
from html import unescape
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from config import get_settings
from models import Article

logger = logging.getLogger("uvicorn.error")

# Generous but safe cap for the provider request payload.
MAX_INPUT_CHARS = 60_000

# Cap on the raw page downloaded before extraction (avoids huge responses).
MAX_PAGE_BYTES = 2_000_000

# NewsAPI's free tier truncates article bodies and appends "[+N chars]".
_TRUNCATED_SUFFIX = re.compile(r"\[\+\d+\s*chars?\]\s*$", re.IGNORECASE)

# Blocks of the article page that carry no story text.
_SKIP_BLOCK_TAGS = re.compile(
    r"<(script|style|noscript|svg|nav|header|footer|aside|form|iframe|figure|figcaption"
    r"|button|label|select|input|textarea)\b.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")


class SummarizeError(Exception):
    """Raised when a summary cannot be produced."""


def _is_unsafe_url(url: str) -> bool:
    """Block non-http(s) schemes and private/loopback/link-local targets (SSRF guard).

    The summary endpoint is public, so an article URL must never make the server
    reach internal addresses (cloud metadata, localhost, LAN hosts, ...).
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return True
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return True

    hostname = parsed.hostname
    if hostname.lower() == "localhost":
        return True

    def _unsafe(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        )

    try:
        ip = ipaddress.ip_address(hostname)
        return _unsafe(ip)
    except ValueError:
        # Hostname — resolve and require every address to be public.
        try:
            infos = socket.getaddrinfo(hostname, None)
        except (socket.gaierror, OSError):
            return True
        try:
            return any(
                _unsafe(ipaddress.ip_address(info[4][0])) for info in infos
            )
        except ValueError:
            return True


@dataclass
class SummaryResult:
    summary: str
    model: str
    cached: bool


def _is_truncated(content: str) -> bool:
    """True when the stored body was cut short by the provider."""
    return bool(_TRUNCATED_SUFFIX.search(content.strip())) or content.strip().endswith("… [+")


def _html_to_text(html_text: str) -> str:
    """Crude but effective HTML-to-text: drop non-content blocks, tags, entities."""
    text = _SKIP_BLOCK_TAGS.sub(" ", html_text)
    text = _TAG_RE.sub(" ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _fetch_full_text(url: str) -> str | None:
    """Fetch the full article page and extract readable text.

    NewsAPI's free tier stores only a truncated snippet, so we grab the complete
    story from the original URL. Returns ``None`` on any failure so the caller
    can fall back to the stored content.
    """
    if _is_unsafe_url(url):
        logger.info("[summarizer] refused to fetch non-public URL: %s", url)
        return None
    try:
        import httpx

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
        with httpx.stream(
            "GET", url, headers=headers, timeout=20, follow_redirects=True
        ) as response:
            response.raise_for_status()
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > MAX_PAGE_BYTES:
                    logger.info("[summarizer] page too large, skipping: %s", url)
                    return None
                chunks.append(chunk)
        html_text = b"".join(chunks).decode("utf-8", errors="ignore")
        text = _html_to_text(html_text)
        if len(text) < 100:
            return None
        return text[:MAX_INPUT_CHARS]
    except Exception as exc:
        logger.info("[summarizer] full-text fetch failed for %s: %s", url, exc)
        return None


def _article_source_text(article: Article) -> str:
    """Best available source text for the summary.

    Prefers the full article text fetched from the original URL whenever the
    stored body is missing or provider-truncated; otherwise falls back to the
    stored content, then the description.
    """
    stored = (article.content or "").strip()
    if article.url and (not stored or _is_truncated(stored)):
        fetched = _fetch_full_text(article.url)
        if fetched:
            return fetched
    if stored:
        return stored
    return (article.summary or "").strip()


def _build_prompt(title: str, body: str) -> str:
    """Compose the summarization prompt from the article title and body."""
    text = f"Title: {title}\n\n{body}".strip()
    return (
        "Write a comprehensive summary of the following news article. Cover the main "
        "story, the key facts and figures, the people or organizations involved, any "
        "important background context, and what happens next or why it matters. Produce "
        "a detailed but readable summary in plain text only — no markdown, no bullet "
        "lists. Do not add opinions or editorializing; stick strictly to what the "
        "article reports.\n\n"
        f"ARTICLE:\n{text[:MAX_INPUT_CHARS]}"
    )


def _call_gemini(settings, prompt: str) -> str:
    """Call the configured Gemini model and return the raw text response.

    The google-genai import is lazy so the rest of the app keeps working even
    if the package is missing, and so tests can patch this function directly.
    """
    try:
        from google import genai
        from google.genai import types as genai_types
    except ImportError as exc:
        raise SummarizeError(
            "google-genai is not installed — run `pip install google-genai`"
        ) from exc

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            # Gemini 3.5 Flash spends part of this budget on internal "thinking"
            # tokens before writing text, so keep it generous or long articles
            # produce truncated summaries (finish_reason=MAX_TOKENS early).
            config=genai_types.GenerateContentConfig(
                temperature=0.4,
                max_output_tokens=4096,
            ),
        )
    except Exception as exc:
        logger.error("[summarizer] Gemini call failed: %s", exc)
        raise SummarizeError(f"AI summarization failed: {exc}") from exc

    return (response.text or "").strip()


def summarize_article(db: Session, article: Article) -> SummaryResult:
    """Return an AI summary for ``article``, generating and caching it on first call.

    The generated summary is stored on ``article.ai_summary`` so subsequent
    requests return instantly without spending Gemini quota.
    """
    settings = get_settings()

    if article.ai_summary:
        return SummaryResult(summary=article.ai_summary, model=settings.GEMINI_MODEL, cached=True)

    if not settings.GEMINI_API_KEY:
        raise SummarizeError(
            "AI summarization is not configured — set GEMINI_API_KEY in Backend/.env "
            "(get a free key at aistudio.google.com)"
        )

    body = _article_source_text(article)
    if not body:
        raise SummarizeError("This article has no text to summarize.")

    summary = _call_gemini(settings, _build_prompt(article.title, body))
    if not summary:
        raise SummarizeError("The AI returned an empty summary.")

    article.ai_summary = summary
    db.commit()
    db.refresh(article)
    return SummaryResult(summary=summary, model=settings.GEMINI_MODEL, cached=False)
