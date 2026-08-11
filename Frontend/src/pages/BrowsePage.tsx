import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Category, Source } from "../types";

export default function BrowsePage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [sources, setSources] = useState<Source[]>([]);

  useEffect(() => {
    api
      .get<Category[]>("/categories")
      .then(setCategories)
      .catch(() => undefined);
    api
      .get<Source[]>("/sources")
      .then(setSources)
      .catch(() => undefined);
  }, []);

  const sourcesByCategory = new Map<number | null, Source[]>();
  for (const source of sources) {
    const key = source.category_id;
    const list = sourcesByCategory.get(key) ?? [];
    list.push(source);
    sourcesByCategory.set(key, list);
  }

  return (
    <div className="page">
      <div className="container">
        <div className="feed-heading">
          <h2>Browse the newsroom</h2>
          <p className="feed-count">Categories &amp; sources you can follow</p>
        </div>

        <section className="browse-section">
          <h3 className="section-title">Categories</h3>
          <div className="category-grid">
            {categories.map((category) => (
              <Link
                key={category.id}
                to={`/search?category=${category.slug}`}
                className="category-card"
              >
                <span className="category-name">{category.name}</span>
                {category.description && (
                  <span className="category-desc">{category.description}</span>
                )}
              </Link>
            ))}
          </div>
        </section>

        <section className="browse-section">
          <h3 className="section-title">Sources</h3>
          {categories.map((category) => {
            const list = sourcesByCategory.get(category.id) ?? [];
            if (list.length === 0) return null;
            return (
              <div key={category.id} className="source-group">
                <h4 className="source-group-title">{category.name}</h4>
                <ul className="source-list">
                  {list.map((source) => (
                    <li key={source.id} className="source-item">
                      <span className="source-item-name">
                        {source.name}
                        {source.url && (
                          <a
                            href={source.url}
                            target="_blank"
                            rel="noreferrer"
                            className="source-item-url"
                            aria-label={`Open ${source.name}`}
                          >
                            ↗
                          </a>
                        )}
                      </span>
                      {source.description && (
                        <span className="source-item-desc">{source.description}</span>
                      )}
                      <Link to={`/search?source_id=${source.id}`} className="link-button">
                        See articles
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
          {sources.filter((s) => s.category_id === null).length > 0 && (
            <div className="source-group">
              <h4 className="source-group-title">Uncategorized</h4>
              <ul className="source-list">
                {sources
                  .filter((s) => s.category_id === null)
                  .map((source) => (
                    <li key={source.id} className="source-item">
                      <span className="source-item-name">{source.name}</span>
                    </li>
                  ))}
              </ul>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
