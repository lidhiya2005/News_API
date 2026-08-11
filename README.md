# NewsHub — News Discovery & Management Platform

A full-stack news discovery and curation platform: browse, search, filter, bookmark,
and manage news articles. The backend imports live stories from **NewsAPI.org**
(optional, free tier), while the frontend provides a polished reading experience.

| Layer    | Stack                                                            |
| -------- | ---------------------------------------------------------------- |
| Backend  | FastAPI, SQLAlchemy 2.0, SQLite, JWT auth, bcrypt                |
| Frontend | React 18, TypeScript, Vite, React Router 6                        |

---

## Project structure

```
News-API/
├── Backend/            # FastAPI REST API
│   ├── routers/        # auth, articles, categories, sources, bookmarks, discovery
│   ├── services/       # NewsAPI.org integration (fetch / search / scheduler)
│   ├── tests/          # 23 end-to-end API tests (pytest + TestClient)
│   ├── main.py         # app entry point
│   ├── seed.py         # demo content + demo user (on first startup)
│   └── .env.example    # copy to .env and fill in secrets
└── Frontend/           # React SPA
    └── src/
        ├── pages/      # Home, Search, Article, Browse, Bookmarks, Login, Register
        ├── components/ # Navbar, ArticleCard, ArticleFeed, Pagination, Footer
        ├── context/    # AuthContext (JWT session)
        ├── hooks/      # useBookmark
        └── api/        # typed API client
```

## Prerequisites

- **Python 3.10+** for the backend
- **Node.js 18+** for the frontend

## Quick start

### 1. Backend (port 8000)

```bash
cd Backend

# create + activate a virtual environment
python -m venv venv
# Windows (Git Bash): source venv/Scripts/activate
# macOS/Linux:       source venv/bin/activate

# install dependencies
pip install -r requirements.txt

# configure secrets (generates .env with a random SECRET_KEY)
cp .env.example .env   # then edit SECRET_KEY / add your NEWS_API_KEY

# run the API (docs at http://localhost:8000/docs)
uvicorn main:app --reload --port 8000
```

### 2. Frontend (port 5173)

```bash
cd Frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies `/api` to the backend,
so no CORS configuration is needed in development.

### Demo account (seeded on first backend startup)

| Email            | Password | Role      |
| ---------------- | -------- | --------- |
| demo@newsapp.com | demo123  | superuser |

## Useful commands

```bash
# Backend tests (23 tests - auth, CRUD, bookmarks, discovery)
cd Backend && ./venv/Scripts/python.exe -m pytest -q

# Frontend typecheck + production build
cd Frontend && npm run build
```

## Environment variables (Backend/.env)

| Variable                  | Default                    | Purpose                            |
| ------------------------- | -------------------------- | ---------------------------------- |
| `DATABASE_URL`            | `sqlite:///./news.db`      | Database connection string         |
| `SECRET_KEY`              | *(dev default)*            | JWT signing key - **change it!**    |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` (7 days)       | Token lifetime                     |
| `CORS_ORIGINS`            | localhost:3000/5173        | Allowed frontend origins           |
| `NEWS_API_KEY`            | *(unset)*                  | Enables live news discovery        |
| `NEWS_AUTO_FETCH`         | `false`                    | Scheduled auto-fetch on/off        |
| `NEWS_FETCH_INTERVAL_MINUTES` | `60`                   | Auto-fetch interval                |
| `SEED_ON_STARTUP`         | `true`                     | Seed demo data on startup          |

> **Security note:** `.env` is gitignored. Never commit real API keys or secrets -
> keep placeholders in `.env.example` only.

## API overview

Interactive docs at **http://localhost:8000/docs**. Highlights:

- `POST /api/auth/register` · `POST /api/auth/login` · `GET /api/auth/me`
- `GET /api/articles` — list/search/filter/sort/paginate
- `GET /api/articles/{id}` — detail (counts a view)
- `GET/POST/PUT/DELETE /api/categories` & `/api/sources`
- `GET/POST/DELETE /api/bookmarks/{article_id}`
- `GET /api/discovery/trending` · `POST /api/discovery/fetch|search` · `GET /api/discovery/status`
