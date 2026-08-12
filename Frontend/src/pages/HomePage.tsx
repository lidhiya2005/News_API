import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Article, DiscoveryStatus } from "../types";
import ArticleFeed from "../components/ArticleFeed";
import { formatViews, timeAgo } from "../utils";
import { Link } from "react-router-dom";

export default function HomePage() {
  const [trending, setTrending] = useState<Article[]>([]);
  const [discovery, setDiscovery] = useState<DiscoveryStatus | null>(null);
  const [breaking, setBreaking] = useState<Article[]>([]);

  useEffect(() => {
    api
      .get<Article[]>("/discovery/trending?limit=6&days=14")
      .then(setTrending)
      .catch(() => undefined);
    api
      .get<DiscoveryStatus>("/discovery/status")
      .then(setDiscovery)
      .catch(() => undefined);
    api
      .get<{ items: Article[] }>("/articles?breaking=true&size=5")
      .then((data) => setBreaking(data.items))
      .catch(() => undefined);
  }, []);

  return (
    <div className="page">
      {breaking.length > 0 && (
        <div className="breaking-bar">
          <span className="breaking-label">⚡ Breaking</span>
          <div className="breaking-titles">
            {breaking.slice(0, 3).map((a) => (
              <Link key={a.id} to={`/article/${a.id}`} className="breaking-title">
                {a.title}
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="container page-grid">
        <div className="page-main">
          <ArticleFeed showHeader={false} />
        </div>

        <aside className="page-side">
          <section className="panel">
            <h3 className="panel-title">🔥 Trending now</h3>
            {trending.length === 0 ? (
              <p className="panel-empty">No trending articles yet.</p>
            ) : (
              <ol className="trending-list">
                {trending.map((a, i) => (
                  <li key={a.id}>
                    <Link to={`/article/${a.id}`} className="trending-item">
                      <span className="trending-rank">{i + 1}</span>
                      <span className="trending-body">
                        <span className="trending-title">{a.title}</span>
                        <span className="trending-meta">
                          {timeAgo(a.published_at)} · {formatViews(a.views)} views
                        </span>
                      </span>
                    </Link>
                  </li>
                ))}
              </ol>
            )}
          </section>

          {discovery && (
            <section className="panel">
              <h3 className="panel-title">📡 Live discovery</h3>
              <dl className="discovery-stats">
                <div>
                  <dt>Provider</dt>
                  <dd>{discovery.provider}</dd>
                </div>
                <div>
                  <dt>Configured</dt>
                  <dd>{discovery.configured ? "Yes" : "No API key"}</dd>
                </div>
                <div>
                  <dt>Auto-fetch</dt>
                  <dd>
                    {discovery.auto_fetch_enabled
                      ? `Every ${discovery.fetch_interval_minutes} min`
                      : "Off"}
                  </dd>
                </div>
                {discovery.last_run && (
                  <div>
                    <dt>Last run</dt>
                    <dd>
                      {discovery.last_run.status} · {discovery.last_run.imported} imported
                    </dd>
                  </div>
                )}
              </dl>
              <Link to="/live" className="btn btn-ghost btn-small panel-cta">
                Open live news →
              </Link>
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}
