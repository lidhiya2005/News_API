import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Bookmark, Page } from "../types";
import { timeAgo } from "../utils";

export default function BookmarksPage() {
  const [page, setPage] = useState<Page<Bookmark> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .get<Page<Bookmark>>("/bookmarks?size=50")
      .then((data) => {
        if (!cancelled) setPage(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load bookmarks");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function remove(bookmark: Bookmark) {
    try {
      await api.delete(`/bookmarks/${bookmark.article.id}`);
      setPage((p) =>
        p ? { ...p, items: p.items.filter((b) => b.id !== bookmark.id), total: p.total - 1 } : p,
      );
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="page">
      <div className="container">
        <div className="feed-heading">
          <h2>Your bookmarks</h2>
          {page && (
            <p className="feed-count">
              {page.total} saved article{page.total === 1 ? "" : "s"}
            </p>
          )}
        </div>

        {loading && <p className="notice">Loading bookmarks…</p>}
        {!loading && error && <p className="notice notice-error">{error}</p>}

        {!loading && !error && page && page.items.length === 0 && (
          <div className="empty-state">
            <p className="empty-emoji" aria-hidden="true">
              🔖
            </p>
            <h3>Nothing saved yet</h3>
            <p>
              Hit the bookmark icon on any article to save it for later.{" "}
              <Link to="/">Browse the feed →</Link>
            </p>
          </div>
        )}

        {page && page.items.length > 0 && (
          <ul className="bookmark-list">
            {page.items.map((bookmark) => {
              const article = bookmark.article;
              return (
                <li key={bookmark.id} className="bookmark-row">
                  <Link to={`/article/${article.id}`} className="bookmark-link">
                    {article.image_url && (
                      <img
                        className="bookmark-thumb"
                        src={article.image_url}
                        alt=""
                        onError={(e) => {
                          (e.currentTarget as HTMLImageElement).style.display = "none";
                        }}
                      />
                    )}
                    <span className="bookmark-text">
                      <span className="bookmark-title">{article.title}</span>
                      <span className="bookmark-meta">
                        {article.category?.name ?? "News"} · {article.source?.name ?? "Unknown"} ·{" "}
                        {timeAgo(article.published_at)}
                      </span>
                    </span>
                  </Link>
                  <button
                    className="btn btn-ghost btn-small"
                    onClick={() => void remove(bookmark)}
                  >
                    Remove
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
