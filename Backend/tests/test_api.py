"""End-to-end API tests using FastAPI's TestClient against a throwaway SQLite DB."""
import os
import tempfile

# Point the app at a throwaway database BEFORE importing it.
_tmp_db = os.path.join(tempfile.gettempdir(), "news_test.db")
if os.path.exists(_tmp_db):
    os.remove(_tmp_db)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db}"
os.environ["SEED_ON_STARTUP"] = "true"

import json  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402

DEMO_EMAIL = "demo@newsapp.com"
DEMO_PASSWORD = "demo123"


@pytest.fixture(scope="module")
def client():
    """TestClient entered as a context manager so the app lifespan runs."""
    with TestClient(app) as test_client:
        yield test_client


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login_demo(client) -> str:
    response = client.post(
        "/api/auth/login",
        data={"username": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


# ---------------------------------------------------------------------------
# Meta & seed data
# ---------------------------------------------------------------------------
def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_seed_data_present(client):
    cats = client.get("/api/categories")
    assert cats.status_code == 200
    assert len(cats.json()) >= 10

    articles = client.get("/api/articles", params={"size": 100})
    assert articles.status_code == 200
    assert articles.json()["total"] >= 30


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def test_register_login_me(client):
    payload = {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "secret123",
        "full_name": "New User",
    }
    created = client.post("/api/auth/register", json=payload)
    assert created.status_code == 201
    token = created.json()["access_token"]
    assert token

    me = client.get("/api/auth/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["email"] == payload["email"]

    login = client.post(
        "/api/auth/login",
        data={"username": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200
    assert login.json()["access_token"]


def test_register_duplicate_email(client):
    payload = {
        "email": "newuser@example.com",
        "username": "anothername",
        "password": "secret123",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 409


def test_login_wrong_password(client):
    response = client.post(
        "/api/auth/login",
        data={"username": DEMO_EMAIL, "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401


# ---------------------------------------------------------------------------
# Articles — discovery
# ---------------------------------------------------------------------------
def test_article_list_pagination_and_filters(client):
    page = client.get("/api/articles", params={"page": 1, "size": 5})
    assert page.status_code == 200
    body = page.json()
    assert body["page"] == 1
    assert body["size"] == 5
    assert len(body["items"]) == 5
    assert body["pages"] >= 1

    tech = client.get("/api/articles", params={"category": "technology", "size": 50})
    assert tech.status_code == 200
    assert tech.json()["total"] > 0
    for item in tech.json()["items"]:
        assert item["category"] is not None
        assert item["category"]["slug"] == "technology"

    featured = client.get("/api/articles", params={"featured": True, "size": 50})
    assert featured.json()["total"] > 0

    search = client.get("/api/articles", params={"q": "climate", "size": 50})
    assert search.status_code == 200

    unknown = client.get("/api/articles", params={"category": "nope-not-real"})
    assert unknown.status_code == 404

    popular = client.get("/api/articles", params={"sort": "popular", "size": 5})
    views = [a["views"] for a in popular.json()["items"]]
    assert views == sorted(views, reverse=True)


def test_article_detail_increments_views(client):
    first = client.get("/api/articles", params={"size": 1}).json()["items"][0]
    before = client.get(f"/api/articles/{first['id']}").json()["views"]
    after = client.get(f"/api/articles/{first['id']}").json()["views"]
    assert after == before + 1


# ---------------------------------------------------------------------------
# Article management (authenticated)
# ---------------------------------------------------------------------------
def test_create_update_delete_article(client):
    token = _login_demo(client)
    headers = auth_headers(token)

    created = client.post(
        "/api/articles",
        headers=headers,
        json={
            "title": "Breaking: Test Article About Quantum Kettles",
            "summary": "A short summary.",
            "content": "Full body of the article.",
            "is_featured": True,
        },
    )
    assert created.status_code == 201
    article = created.json()
    assert article["slug"].startswith("breaking-test-article")

    updated = client.put(
        f"/api/articles/{article['id']}",
        headers=headers,
        json={"title": "Updated: Test Article About Quantum Kettles", "is_featured": False},
    )
    assert updated.status_code == 200
    assert updated.json()["is_featured"] is False

    deleted = client.delete(f"/api/articles/{article['id']}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/articles/{article['id']}").status_code == 404


def test_create_article_requires_auth(client):
    response = client.post("/api/articles", json={"title": "No auth here"})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Categories & sources management
# ---------------------------------------------------------------------------
def test_create_category_and_list(client):
    token = _login_demo(client)
    headers = auth_headers(token)

    created = client.post("/api/categories", headers=headers, json={"name": "Gadgets"})
    assert created.status_code == 201
    assert created.json()["slug"] == "gadgets"

    listed = client.get("/api/categories")
    assert any(c["slug"] == "gadgets" for c in listed.json())


def test_sources_list_and_management(client):
    listed = client.get("/api/sources")
    assert listed.status_code == 200
    assert len(listed.json()) >= 10

    token = _login_demo(client)
    headers = auth_headers(token)

    created = client.post(
        "/api/sources",
        headers=headers,
        json={"name": "My News Wire", "url": "https://example.com", "language": "en"},
    )
    assert created.status_code == 201
    assert created.json()["slug"] == "my-news-wire"

    updated = client.put(
        f"/api/sources/{created.json()['id']}",
        headers=headers,
        json={"description": "A test source"},
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "A test source"


# ---------------------------------------------------------------------------
# Bookmarks
# ---------------------------------------------------------------------------
def test_bookmark_flow(client):
    token = _login_demo(client)
    headers = auth_headers(token)

    article = client.get("/api/articles", params={"size": 1}).json()["items"][0]
    article_id = article["id"]

    added = client.post(f"/api/bookmarks/{article_id}", headers=headers)
    assert added.status_code == 201

    bookmarks = client.get("/api/bookmarks", headers=headers)
    assert bookmarks.status_code == 200
    assert bookmarks.json()["total"] >= 1

    # Duplicate bookmark -> 409
    dup = client.post(f"/api/bookmarks/{article_id}", headers=headers)
    assert dup.status_code == 409

    removed = client.delete(f"/api/bookmarks/{article_id}", headers=headers)
    assert removed.status_code == 204

    gone = client.delete(f"/api/bookmarks/{article_id}", headers=headers)
    assert gone.status_code == 404


def test_bookmarks_require_auth(client):
    assert client.get("/api/bookmarks").status_code == 401


# ---------------------------------------------------------------------------
# Discovery (third-party API integration)
# ---------------------------------------------------------------------------
def fake_fetch_json(endpoint, params):
    """Stand-in for the provider call — returns a small fake NewsAPI payload."""
    category = params.get("category", "general")
    count = 2 if endpoint == "top-headlines" else 3
    articles = []
    for i in range(count):
        articles.append(
            {
                "source": {"id": None, "name": f"Test Wire {category}"},
                "author": "Test Author",
                "title": f"{category.title()} headline {i + 1}",
                "description": "A test summary.",
                "url": f"https://example.com/{category}/{i + 1}",
                "urlToImage": None,
                "publishedAt": "2025-08-01T10:00:00Z",
                "content": "Test body content.",
            }
        )
    return {"status": "ok", "totalResults": count, "articles": articles}


def test_trending(client):
    response = client.get("/api/discovery/trending", params={"limit": 5})
    assert response.status_code == 200
    assert len(response.json()) <= 5


def test_fetch_requires_api_key(client):
    token = _login_demo(client)
    response = client.post("/api/discovery/fetch", headers=auth_headers(token))
    # Without NEWS_API_KEY configured, we expect a clear 400.
    assert response.status_code == 400
    assert "NEWS_API_KEY" in response.json()["detail"]


def test_discovery_fetch_mocked(client, monkeypatch):
    monkeypatch.setattr("services.news_fetcher._fetch_json", fake_fetch_json)
    token = _login_demo(client)

    response = client.post(
        "/api/discovery/fetch",
        headers=auth_headers(token),
        params={"category": "technology"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["imported"] == 2
    assert "technology" in body["categories"]

    # Imported articles are now searchable through the normal feed.
    articles = client.get(
        "/api/articles",
        params={"category": "technology", "q": "headline", "size": 10},
    )
    assert articles.json()["total"] >= 2


def test_discovery_search_mocked(client, monkeypatch):
    monkeypatch.setattr("services.news_fetcher._fetch_json", fake_fetch_json)
    token = _login_demo(client)

    response = client.post(
        "/api/discovery/search",
        headers=auth_headers(token),
        params={"q": "climate"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["imported"] == 3
    assert body["trigger"] == "search"


def test_discovery_status_and_runs(client):
    status = client.get("/api/discovery/status")
    assert status.status_code == 200
    body = status.json()
    assert body["configured"] is False  # no API key in the test environment
    assert body["provider"] == "NewsAPI.org"
    assert "last_run" in body

    runs = client.get("/api/discovery/runs")
    assert runs.status_code == 200
    assert len(runs.json()) >= 1
    assert all(r["status"] in ("success", "error") for r in runs.json())


def test_discovery_requires_auth(client):
    assert client.post("/api/discovery/fetch").status_code == 401
    assert client.post("/api/discovery/search", params={"q": "news"}).status_code == 401


def test_discovery_invalid_category(client):
    token = _login_demo(client)
    response = client.post(
        "/api/discovery/fetch",
        headers=auth_headers(token),
        params={"category": "politics"},
    )
    assert response.status_code == 400
    assert "Unsupported category" in response.json()["detail"]


def _fake_settings():
    class _Fake:
        NEWS_API_KEY = "test-key"
        NEWS_API_BASE_URL = "https://newsapi.org/v2"

    return _Fake()


class _UnreadableResponse:
    status_code = 200
    text = "<html><body>error page</body></html>"

    def raise_for_status(self):
        pass

    def json(self):
        raise json.JSONDecodeError("not json", self.text, 0)


class _RateLimitedResponse:
    status_code = 429
    text = "rate limited"

    def raise_for_status(self):
        pass

    def json(self):
        raise AssertionError("json should not be called for 429")


def test_discovery_unreadable_provider_response(client, monkeypatch):
    monkeypatch.setattr("services.news_fetcher.get_settings", lambda: _fake_settings())
    monkeypatch.setattr(
        "services.news_fetcher.httpx.get", lambda *args, **kwargs: _UnreadableResponse()
    )
    token = _login_demo(client)
    response = client.post("/api/discovery/fetch", headers=auth_headers(token))
    assert response.status_code == 502
    assert "unreadable" in response.json()["detail"]


def test_discovery_rate_limited(client, monkeypatch):
    monkeypatch.setattr("services.news_fetcher.get_settings", lambda: _fake_settings())
    monkeypatch.setattr(
        "services.news_fetcher.httpx.get", lambda *args, **kwargs: _RateLimitedResponse()
    )
    token = _login_demo(client)
    response = client.post("/api/discovery/fetch", headers=auth_headers(token))
    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"].lower()
