import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, toQuery } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { Article, DiscoveryRun, DiscoveryStatus, Page } from "../types";
import ArticleCard from "../components/ArticleCard";
import { timeAgo } from "../utils";

const NEWSAPI_CATEGORIES = [
  "business",
  "entertainment",
  "general",
  "health",
  "science",
  "sports",
  "technology",
] as const;

const COUNTRIES = [
  { code: "us", name: "United States" },
  { code: "gb", name: "United Kingdom" },
  { code: "ca", name: "Canada" },
  { code: "au", name: "Australia" },
  { code: "in", name: "India" },
  { code: "de", name: "Germany" },
  { code: "fr", name: "France" },
  { code: "jp", name: "Japan" },
] as const;

const PAGE_SIZES = [5, 10, 20, 50] as const;

interface LiveResults {
  kind: "category" | "q";
  value: string;
  from?: string;
  to?: string;
}

export default function LiveNewsPage() {
  const { user } = useAuth();
  const [status, setStatus] = useState<DiscoveryStatus | null>(null);
  const [runs, setRuns] = useState<DiscoveryRun[]>([]);

  const [category, setCategory] = useState<(typeof NEWSAPI_CATEGORIES)[number]>("technology");
  const [country, setCountry] = useState("us");
  const [pageSize, setPageSize] = useState(10);

  const [query, setQuery] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  const [busy, setBusy] = useState<"fetch" | "search" | null>(null);
  const [lastRun, setLastRun] = useState<DiscoveryRun | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [results, setResults] = useState<LiveResults | null>(null);
  const [articles, setArticles] = useState<Article[]>([]);
  const [loadingArticles, setLoadingArticles] = useState(false);
  const [resultsError, setResultsError] = useState<string | null>(null);

  const refreshRuns = useCallback(() => {
    api
      .get<DiscoveryRun[]>("/discovery/runs?limit=10")
      .then(setRuns)
      .catch(() => undefined);
  }, []);

  const refreshStatus = useCallback(() => {
    api
      .get<DiscoveryStatus>("/discovery/status")
      .then(setStatus)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    refreshStatus();
    refreshRuns();
  }, [refreshRuns, refreshStatus]);

  // Load the articles belonging to the most recent fetch/search from the feed.
  useEffect(() => {
    if (!results) {
      setArticles([]);
      return;
    }
    let cancelled = false;
    setLoadingArticles(true);
    setResultsError(null);
    // The provider's "general" topic maps to our seeded "world" category.
    const categorySlug = results.kind === "category" && results.value === "general" ? "world" : results.value;
    api
      .get<Page<Article>>(
        `/articles${toQuery({
          ...(results.kind === "category"
            ? { category: categorySlug }
            : { q: results.value || undefined }),
          from_date: results.from || undefined,
          to_date: results.to || undefined,
          sort: "newest",
          size: 24,
        })}`,
      )
      .then((page) => {
        if (!cancelled) setArticles(page.items);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setResultsError(err instanceof Error ? err.message : "Could not load imported articles");
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingArticles(false);
      });
    return () => {
      cancelled = true;
    };
  }, [results]);

  async function runFetch() {
    setBusy("fetch");
    setError(null);
    try {
      const run = await api.post<DiscoveryRun>(
        `/discovery/fetch${toQuery({ category, country, page_size: pageSize })}`,
      );
      setLastRun(run);
      setResults({ kind: "category", value: category });
      refreshRuns();
      refreshStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Live fetch failed");
    } finally {
      setBusy(null);
    }
  }

  async function runSearch() {
    const q = query.trim();
    if (q.length < 2) {
      setError("Enter at least 2 characters to search live news.");
      return;
    }
    if (fromDate && toDate && fromDate > toDate) {
      setError("The 'From' date must be on or before the 'To' date.");
      return;
    }
    setBusy("search");
    setError(null);
    try {
      const run = await api.post<DiscoveryRun>(
        `/discovery/search${toQuery({
          q,
          page_size: pageSize,
          from_date: fromDate || undefined,
          to_date: toDate || undefined,
        })}`,
      );
      setLastRun(run);
      setResults({ kind: "q", value: q, from: fromDate || undefined, to: toDate || undefined });
      refreshRuns();
      refreshStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Live search failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="page">
      <div className="container page-grid">
        <div className="page-main">
          <div className="feed-heading live-heading">
            <div>
              <h2>Live news</h2>
              <p className="feed-count">
                Pull fresh headlines &amp; archived stories straight from NewsAPI.org
              </p>
            </div>
            {status && (
              <span className={`live-badge${status.configured ? " on" : ""}`}>
                {status.configured ? "● Connected" : "○ No API key"}
              </span>
            )}
          </div>

          {!user && (
            <p className="notice">
              <Link to="/login">Log in</Link> to fetch live news from the provider.
            </p>
          )}

          {user && (
            <>
              <section className="panel live-panel">
                <h3 className="panel-title">⚡ Fetch top headlines</h3>
                <div className="toolbar-row">
                  <label className="toolbar-field">
                    <span>Category</span>
                    <select
                      className="toolbar-select"
                      value={category}
                      onChange={(e) => setCategory(e.target.value as typeof category)}
                      aria-label="Headlines category"
                    >
                      {NEWSAPI_CATEGORIES.map((c) => (
                        <option key={c} value={c}>
                          {c.charAt(0).toUpperCase() + c.slice(1)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="toolbar-field">
                    <span>Country</span>
                    <select
                      className="toolbar-select"
                      value={country}
                      onChange={(e) => setCountry(e.target.value)}
                      aria-label="Headlines country"
                    >
                      {COUNTRIES.map((c) => (
                        <option key={c.code} value={c.code}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="toolbar-field">
                    <span>How many</span>
                    <select
                      className="toolbar-select"
                      value={pageSize}
                      onChange={(e) => setPageSize(Number(e.target.value))}
                      aria-label="Number of headlines"
                    >
                      {PAGE_SIZES.map((n) => (
                        <option key={n} value={n}>
                          {n}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    className="btn btn-primary live-action"
                    onClick={() => void runFetch()}
                    disabled={busy !== null}
                  >
                    {busy === "fetch" ? "Fetching…" : "Fetch headlines"}
                  </button>
                </div>
                <p className="live-hint">Newest stories from right now, imported into your feed.</p>
              </section>

              <section className="panel live-panel">
                <h3 className="panel-title">🔎 Search live news — past &amp; present</h3>
                <div className="toolbar-row">
                  <label className="toolbar-field toolbar-field-grow">
                    <span>Keyword</span>
                    <input
                      type="search"
                      className="toolbar-search"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="e.g. climate, AI, markets…"
                      aria-label="Live news keyword"
                    />
                  </label>
                  <label className="toolbar-field">
                    <span>From</span>
                    <input
                      type="date"
                      className="toolbar-date"
                      value={fromDate}
                      onChange={(e) => setFromDate(e.target.value)}
                      aria-label="Published from"
                    />
                  </label>
                  <label className="toolbar-field">
                    <span>To</span>
                    <input
                      type="date"
                      className="toolbar-date"
                      value={toDate}
                      onChange={(e) => setToDate(e.target.value)}
                      aria-label="Published to"
                    />
                  </label>
                  <button
                    type="button"
                    className="btn btn-primary live-action"
                    onClick={() => void runSearch()}
                    disabled={busy !== null}
                  >
                    {busy === "search" ? "Searching…" : "Search"}
                  </button>
                </div>
                <p className="live-hint">
                  Searches the provider's archive — add dates to reach back into the past (free
                  tier covers roughly the last month).
                </p>
              </section>

              {error && <p className="notice notice-error">{error}</p>}

              {lastRun && lastRun.status === "success" && (
                <p className="notice notice-success">
                  ✓ Imported {lastRun.imported} article
                  {lastRun.imported === 1 ? "" : "s"}
                  {lastRun.skipped > 0 ? ` · ${lastRun.skipped} skipped (duplicates)` : ""} —{" "}
                  {lastRun.message}
                </p>
              )}

              {resultsError && <p className="notice notice-error">{resultsError}</p>}

              <div className="feed-heading">
                <h3 className="section-title section-title-live">
                  {results ? (
                    results.kind === "category" ? (
                      <>
                        Top headlines ·{" "}
                        <span className="section-title-accent">{results.value}</span>
                      </>
                    ) : (
                      <>
                        Results for <em>“{results.value}”</em>
                      </>
                    )
                  ) : (
                    "Imported stories"
                  )}
                </h3>
                {!loadingArticles && (
                  <p className="feed-count">{articles.length} article{articles.length === 1 ? "" : "s"}</p>
                )}
              </div>

              {loadingArticles && (
                <div className="grid grid-loading">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <div key={i} className="card skeleton" aria-hidden="true" />
                  ))}
                </div>
              )}

              {!loadingArticles && articles.length > 0 && (
                <div className="grid">
                  {articles.map((article) => (
                    <ArticleCard key={article.id} article={article} />
                  ))}
                </div>
              )}

              {!loadingArticles && results && articles.length === 0 && (
                <div className="empty-state">
                  <p className="empty-emoji" aria-hidden="true">
                    📡
                  </p>
                  <h3>Nothing imported yet</h3>
                  <p>Run a fetch or search above — new stories will appear here.</p>
                </div>
              )}

              {!loadingArticles && !results && (
                <div className="empty-state">
                  <p className="empty-emoji" aria-hidden="true">
                    🗞️
                  </p>
                  <h3>Your live news console</h3>
                  <p>
                    Fetch today's headlines or search the archive, then open any story for full
                    details.
                  </p>
                </div>
              )}
            </>
          )}
        </div>

        <aside className="page-side">
          {status && (
            <section className="panel">
              <h3 className="panel-title">📡 Discovery status</h3>
              <dl className="discovery-stats">
                <div>
                  <dt>Provider</dt>
                  <dd>{status.provider}</dd>
                </div>
                <div>
                  <dt>Configured</dt>
                  <dd>{status.configured ? "Yes" : "No API key"}</dd>
                </div>
                <div>
                  <dt>Auto-fetch</dt>
                  <dd>
                    {status.auto_fetch_enabled
                      ? `Every ${status.fetch_interval_minutes} min`
                      : "Off"}
                  </dd>
                </div>
                {status.last_run && (
                  <div>
                    <dt>Last run</dt>
                    <dd>
                      {status.last_run.status} · {status.last_run.imported} imported
                    </dd>
                  </div>
                )}
              </dl>
            </section>
          )}

          <section className="panel">
            <h3 className="panel-title">🕘 Recent runs</h3>
            {runs.length === 0 ? (
              <p className="panel-empty">No discovery runs yet.</p>
            ) : (
              <ul className="runs-list">
                {runs.map((run) => (
                  <li key={run.id} className="run-row">
                    <span className={`run-dot run-dot-${run.status}`} aria-hidden="true" />
                    <span className="run-body">
                      <span className="run-title">
                        {run.trigger === "search"
                          ? "Search"
                          : run.trigger === "auto"
                            ? "Auto"
                            : "Headlines"}
                        {run.categories.length > 0 && ` · ${run.categories.join(", ")}`}
                      </span>
                      <span className="run-meta">
                        {run.status} · {run.imported} imported · {timeAgo(run.started_at)}
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </aside>
      </div>
    </div>
  );
}
