import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Article, ArticleSummary } from "../types";
import { formatDate, formatViews } from "../utils";
import { useBookmark } from "../hooks/useBookmark";

export default function ArticlePage() {
  const { id } = useParams<{ id: string }>();
  const articleId = Number.parseInt(id ?? "0", 10);
  const [article, setArticle] = useState<Article | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { isSaved, toggle, busy } = useBookmark(articleId);

  const [summary, setSummary] = useState<ArticleSummary | null>(null);
  const [summaryBusy, setSummaryBusy] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);

  // Tracks the article currently on screen so in-flight requests from a
  // previous article can be discarded (closure-captured articleId can't).
  const currentIdRef = useRef(articleId);
  currentIdRef.current = articleId;

  useEffect(() => {
    if (!Number.isFinite(articleId) || articleId <= 0) {
      setError("Article not found");
      return;
    }
    let cancelled = false;
    // Reset AI summary state when switching between articles on this route.
    setSummary(null);
    setSummaryError(null);
    setSummaryBusy(false);
    api
      .get<Article>(`/articles/${articleId}`)
      .then((data) => {
        if (!cancelled) {
          setArticle(data);
          // A previously generated summary ships with the article payload.
          if (data.ai_summary) {
            setSummary({ summary: data.ai_summary, model: "", cached: true });
          }
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Article not found");
      });
    return () => {
      cancelled = true;
    };
  }, [articleId]);

  async function generateSummary() {
    const targetId = articleId;
    setSummaryBusy(true);
    setSummaryError(null);
    try {
      const result = await api.post<ArticleSummary>(`/articles/${targetId}/summary`);
      // Ignore the response if the user navigated to another article meanwhile.
      if (targetId !== currentIdRef.current) return;
      setSummary(result);
      // Keep the article payload in sync so a later visit shows the cached summary.
      setArticle((prev) =>
        prev && prev.id === targetId ? { ...prev, ai_summary: result.summary } : prev,
      );
    } catch (err) {
      if (targetId === currentIdRef.current) {
        setSummaryError(err instanceof Error ? err.message : "Could not generate the summary.");
      }
    } finally {
      if (targetId === currentIdRef.current) setSummaryBusy(false);
    }
  }

  // Auto-generate the AI summary as soon as the article opens (no login needed).
  useEffect(() => {
    if (!article || article.ai_summary || summary || summaryBusy || summaryError) return;
    void generateSummary();
  }, [article]); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) {
    return (
      <div className="page">
        <div className="container empty-state">
          <p className="empty-emoji" aria-hidden="true">
            🧐
          </p>
          <h3>{error}</h3>
          <Link to="/" className="btn btn-primary">
            Back to home
          </Link>
        </div>
      </div>
    );
  }

  if (!article) {
    return (
      <div className="page">
        <div className="container">
          <div className="article skeleton-article" aria-hidden="true" />
        </div>
      </div>
    );
  }

  const paragraphs = (article.content ?? article.summary ?? "")
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean);

  return (
    <div className="page">
      <div className="container article-wrap">
        <nav className="breadcrumbs" aria-label="Breadcrumb">
          <Link to="/">Home</Link>
          <span aria-hidden="true">/</span>
          {article.category ? (
            <Link to={`/search?category=${article.category.slug}`}>
              {article.category.name}
            </Link>
          ) : (
            <span>Article</span>
          )}
        </nav>

        <article className="article">
          <header className="article-header">
            <div className="card-tags">
              {article.category && (
                <Link to={`/search?category=${article.category.slug}`} className="pill pill-category">
                  {article.category.name}
                </Link>
              )}
              {article.is_breaking && <span className="pill pill-breaking">Breaking</span>}
              {article.is_featured && <span className="pill pill-featured">Featured</span>}
            </div>

            <h1 className="article-title">{article.title}</h1>
            {article.summary && article.summary !== article.title && (
              <p className="article-deck">{article.summary}</p>
            )}

            <div className="article-meta">
              <span className="avatar avatar-lg" aria-hidden="true">
                {(article.author ?? article.source?.name ?? "N")
                  .split(/\s+/)
                  .map((w) => w[0]?.toUpperCase() ?? "")
                  .slice(0, 2)
                  .join("")}
              </span>
              <div className="article-meta-text">
                <span className="article-byline">
                  {article.author ?? article.source?.name ?? "NewsHub Editorial"}
                </span>
                <span className="article-meta-sub">
                  {article.source?.name ?? "Unknown source"} · {formatDate(article.published_at)} ·{" "}
                  {formatViews(article.views)} views
                </span>
              </div>
              <button
                className={`btn bookmark-cta${isSaved ? " saved" : ""}`}
                onClick={() => void toggle()}
                disabled={busy}
              >
                {isSaved ? "✓ Saved" : "Save for later"}
              </button>
            </div>
          </header>

          {article.image_url && (
            <img
              className="article-hero"
              src={article.image_url}
              alt=""
              onError={(e) => {
                (e.currentTarget as HTMLImageElement).style.display = "none";
              }}
            />
          )}

          <div className="article-body">
            {summary && <p className="article-ai-summary">{summary.summary}</p>}
            {!summary && summaryBusy && (
              <p className="ai-summary-inline" role="status" aria-live="polite">
                Summarizing this article…
              </p>
            )}
            {!summary && summaryError && (
              <p className="ai-summary-inline">
                {summaryError}{" "}
                <button
                  type="button"
                  className="link-button"
                  onClick={() => void generateSummary()}
                >
                  Try again
                </button>
              </p>
            )}
            {paragraphs.length > 0 ? (
              paragraphs.map((p, i) => <p key={i}>{p}</p>)
            ) : (
              <p>No content available for this article yet.</p>
            )}
          </div>

          {article.url && (
            <p className="article-source-link">
              <a href={article.url} target="_blank" rel="noreferrer">
                Read the full story at {article.source?.name ?? "the source"} ↗
              </a>
            </p>
          )}
        </article>
      </div>
    </div>
  );
}
