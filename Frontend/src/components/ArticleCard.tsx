import { Link } from "react-router-dom";
import type { Article } from "../types";
import { formatViews, timeAgo } from "../utils";
import { useBookmark } from "../hooks/useBookmark";

interface ArticleCardProps {
  article: Article;
  className?: string;
}

export default function ArticleCard({ article, className = "" }: ArticleCardProps) {
  const { isSaved, toggle, busy } = useBookmark(article.id);

  return (
    <article className={`card article-card ${className}`}>
      <Link to={`/article/${article.id}`} className="card-media-link">
        {article.image_url ? (
          <img
            className="card-media"
            src={article.image_url}
            alt=""
            loading="lazy"
            onError={(e) => {
              (e.currentTarget as HTMLImageElement).style.display = "none";
            }}
          />
        ) : (
          <div className="card-media card-media-placeholder" aria-hidden="true" />
        )}
      </Link>

      <div className="card-body">
        <div className="card-tags">
          {article.category && (
            <Link to={`/search?category=${article.category.slug}`} className="pill pill-category">
              {article.category.name}
            </Link>
          )}
          {article.is_breaking && <span className="pill pill-breaking">Breaking</span>}
          {article.is_featured && <span className="pill pill-featured">Featured</span>}
        </div>

        <h3 className="card-title">
          <Link to={`/article/${article.id}`}>{article.title}</Link>
        </h3>

        {article.summary && <p className="card-summary">{article.summary}</p>}

        <div className="card-meta">
          <span className="meta-source">{article.source?.name ?? "Unknown source"}</span>
          <span className="meta-dot" aria-hidden="true">
            ·
          </span>
          <span className="meta-time">{timeAgo(article.published_at)}</span>
          <span className="meta-dot" aria-hidden="true">
            ·
          </span>
          <span className="meta-views">{formatViews(article.views)} views</span>

          <button
            className={`bookmark-btn${isSaved ? " saved" : ""}`}
            onClick={() => void toggle()}
            disabled={busy}
            title={isSaved ? "Remove bookmark" : "Save for later"}
            aria-label={isSaved ? "Remove bookmark" : "Save for later"}
            aria-pressed={isSaved}
          >
            <svg
              viewBox="0 0 24 24"
              fill={isSaved ? "currentColor" : "none"}
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path
                d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>
      </div>
    </article>
  );
}
