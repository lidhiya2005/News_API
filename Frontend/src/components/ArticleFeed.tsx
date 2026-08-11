import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, toQuery } from "../api/client";
import type { Article, ArticleSort, Category, Page } from "../types";
import ArticleCard from "./ArticleCard";
import Pagination from "./Pagination";

function parsePage(value: string | null): number {
  const n = Number.parseInt(value ?? "1", 10);
  return Number.isFinite(n) && n > 0 ? n : 1;
}

export default function ArticleFeed({ showHeader = true }: { showHeader?: boolean }) {
  const [searchParams, setSearchParams] = useSearchParams();

  const q = searchParams.get("q") ?? "";
  const category = searchParams.get("category") ?? "";
  const sort = (searchParams.get("sort") ?? "newest") as ArticleSort;
  const page = parsePage(searchParams.get("page"));
  const featured = searchParams.get("featured") === "1";
  const breaking = searchParams.get("breaking") === "1";

  const [input, setInput] = useState(q);
  const [categories, setCategories] = useState<Category[]>([]);
  const [result, setResult] = useState<Page<Article> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => setInput(q), [q]);

  useEffect(() => {
    api
      .get<Category[]>("/categories")
      .then(setCategories)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .get<Page<Article>>(
        `/articles${toQuery({
          q: q || undefined,
          category: category || undefined,
          sort,
          featured: featured ? true : undefined,
          breaking: breaking ? true : undefined,
          page,
          size: 12,
        })}`,
      )
      .then((data) => {
        if (!cancelled) setResult(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load articles");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [q, category, sort, page, featured, breaking]);

  function apply(updates: Record<string, string | null>) {
    const next = new URLSearchParams(searchParams);
    for (const [key, value] of Object.entries(updates)) {
      if (value === null || value === "" || value === "newest") next.delete(key);
      else next.set(key, value);
    }
    setSearchParams(next);
  }

  const submitSearch = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      apply({ q: input.trim() || null });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [input, searchParams],
  );

  function toggleFlag(flag: "featured" | "breaking") {
    const active = flag === "featured" ? featured : breaking;
    apply({ [flag]: active ? null : "1" });
  }

  return (
    <section className="feed">
      <form className="feed-toolbar" onSubmit={submitSearch}>
        <div className="toolbar-row">
          <input
            type="search"
            className="toolbar-search"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Search titles, summaries &amp; content…"
            aria-label="Search articles"
          />
          <select
            className="toolbar-select"
            value={category}
            onChange={(e) => apply({ category: e.target.value || null })}
            aria-label="Filter by category"
          >
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c.id} value={c.slug}>
                {c.name}
              </option>
            ))}
          </select>
          <select
            className="toolbar-select"
            value={sort}
            onChange={(e) => apply({ sort: e.target.value || null })}
            aria-label="Sort articles"
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
            <option value="popular">Most popular</option>
            <option value="title">By title</option>
          </select>
        </div>
        <div className="toolbar-row toolbar-row-secondary">
          <button
            type="button"
            className={`chip${featured ? " chip-on" : ""}`}
            onClick={() => toggleFlag("featured")}
            aria-pressed={featured}
          >
            ★ Featured
          </button>
          <button
            type="button"
            className={`chip${breaking ? " chip-on" : ""}`}
            onClick={() => toggleFlag("breaking")}
            aria-pressed={breaking}
          >
            ⚡ Breaking
          </button>
          <button type="submit" className="btn btn-primary btn-small">
            Search
          </button>
          {(q || category || sort !== "newest" || featured || breaking || page > 1) && (
            <button
              type="button"
              className="link-button"
              onClick={() => setSearchParams(new URLSearchParams())}
            >
              Clear filters
            </button>
          )}
        </div>
      </form>

      {showHeader && (
        <div className="feed-heading">
          <h2>
            {q ? (
              <>
                Results for <em>“{q}”</em>
              </>
            ) : (
              "Latest stories"
            )}
          </h2>
          {result && (
            <p className="feed-count">
              {result.total} article{result.total === 1 ? "" : "s"}
            </p>
          )}
        </div>
      )}

      {loading && (
        <div className="grid grid-loading">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="card skeleton" aria-hidden="true" />
          ))}
        </div>
      )}

      {!loading && error && <p className="notice notice-error">{error}</p>}

      {!loading && !error && result && result.items.length === 0 && (
        <div className="empty-state">
          <p className="empty-emoji" aria-hidden="true">
            🗞️
          </p>
          <h3>No articles found</h3>
          <p>Try a different search term, category, or clear the filters.</p>
        </div>
      )}

      {!loading && !error && result && result.items.length > 0 && (
        <>
          <div className="grid">
            {result.items.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>
          <Pagination
            page={page}
            pages={result.pages}
            total={result.total}
            onPage={(p) => apply({ page: p === 1 ? null : String(p) })}
          />
        </>
      )}
    </section>
  );
}
