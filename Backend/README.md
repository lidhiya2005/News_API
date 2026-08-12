# News Discovery & Management System — Backend

FastAPI backend for discovering, managing, and curating news articles.
Built with **FastAPI**, **SQLAlchemy 2.0**, **SQLite** (default), **JWT** auth,
and **bcrypt** password hashing.

## Features

- **Auth** — register, login (JWT), current-user profile
- **Articles** — CRUD, full-text search, filtering (category / source / featured /
  breaking / date range), sorting, pagination, view tracking
- **Categories** — browse + authenticated management
- **Sources** — browse + authenticated management
- **Bookmarks** — save articles to read later (per user)
- **Discovery** — trending articles, live top-headlines fetch, live keyword search,
  run history + status, and an opt-in scheduled auto-fetch — all via NewsAPI.org
  (optional, needs a free API key)
- **Seed data** — realistic demo content + a demo account on first startup
- Interactive docs at `/docs`

## Quick start

```bash
cd Backend

# 1. Create and activate a virtual environment
python -m venv venv
# Windows (PowerShell): venv\Scripts\Activate.ps1
# Windows (Git Bash):   source venv/Scripts/activate
# macOS/Linux:          source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) configure environment
cp .env.example .env   # then edit SECRET_KEY / add NEWS_API_KEY

# 4. Run the server
uvicorn main:app --reload --port 8000
```

The server is then available at `http://localhost:8000` with docs at
`http://localhost:8000/docs`.

## Demo account (seeded on first run)

| Email             | Password  | Role       |
|-------------------|-----------|------------|
| demo@newsapp.com  | demo123   | superuser  |

## Main endpoints

| Method | Path                              | Auth | Description                          |
|--------|-----------------------------------|------|--------------------------------------|
| POST   | `/api/auth/register`              | —    | Create account, returns JWT          |
| POST   | `/api/auth/login`                 | —    | Login (form: `username`=email)       |
| GET    | `/api/auth/me`                    | ✔    | Current user profile                 |
| GET    | `/api/articles`                   | —    | List / search / filter / paginate    |
| GET    | `/api/articles/{id}`              | —    | Article detail (counts a view)       |
| POST   | `/api/articles`                   | ✔    | Create article                       |
| PUT    | `/api/articles/{id}`              | ✔    | Update article                       |
| DELETE | `/api/articles/{id}`              | ✔    | Delete article                       |
| POST   | `/api/articles/{id}/summary`       | —    | AI summary of an article (Gemini, public; fetches full text when the provider truncated it) |
| GET    | `/api/categories`                 | —    | List categories                      |
| GET    | `/api/sources`                    | —    | List sources                         |
| GET    | `/api/bookmarks`                  | ✔    | My bookmarks                         |
| POST   | `/api/bookmarks/{article_id}`     | ✔    | Bookmark an article                  |
| DELETE | `/api/bookmarks/{article_id}`     | ✔    | Remove bookmark                      |
| GET    | `/api/discovery/trending`         | —    | Most-viewed articles (7 days)        |
| POST   | `/api/discovery/fetch`            | ✔    | Pull live top headlines (NewsAPI)    |
| POST   | `/api/discovery/search`           | ✔    | Search the provider for a keyword    |
| GET    | `/api/discovery/runs`             | —    | Recent discovery run history         |
| GET    | `/api/discovery/status`           | —    | Integration status + last run        |
| GET    | `/api/health`                     | —    | Health check                         |

### Articles query example

```
GET /api/articles?q=climate&category=environment&sort=popular&page=1&size=10
```

## Environment variables (see `.env.example`)

| Variable                  | Default                          | Purpose                          |
|---------------------------|----------------------------------|----------------------------------|
| `DATABASE_URL`            | `sqlite:///./news.db`            | Database connection string       |
| `SECRET_KEY`              | dev value                        | JWT signing key (change it!)     |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` (7 days)             | Token lifetime                   |
| `CORS_ORIGINS`            | localhost:3000/5173              | Allowed frontend origins         |
| `NEWS_API_KEY`            | *(unset)*                        | Enable live discovery via NewsAPI|
| `NEWS_AUTO_FETCH`         | `false`                          | Scheduled auto-fetch on/off      |
| `NEWS_FETCH_INTERVAL_MINUTES` | `60`                         | Auto-fetch interval              |
| `NEWS_COUNTRY`            | `us`                             | Default country for headlines    |
| `NEWS_AUTO_CATEGORIES`    | `technology,business,...`        | Categories fetched on schedule   |
| `GEMINI_API_KEY`          | *(unset)*                        | Enable AI article summaries      |
| `GEMINI_MODEL`            | `gemini-3.5-flash`               | Model used for AI summaries      |
| `SEED_ON_STARTUP`         | `true`                           | Seed demo data on startup        |

## Running tests

```bash
pip install -r requirements-dev.txt
pytest
```
