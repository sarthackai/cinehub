# CineHub — AI-Powered Real-Time OTT Content Recommendation Platform

CineHub is a full-stack, production-style streaming content platform built to demonstrate real machine learning, real-time data engineering, and modern full-stack development — not a toy demo. It aggregates live movie and TV metadata from TMDB, stores it in a normalized PostgreSQL database, and serves personalized, explainable recommendations through a hybrid ML recommendation engine.

> Built as an end-to-end AI/ML portfolio project covering authentication, real-time data pipelines, hybrid recommendation systems, semantic search, and a full React frontend.

---

## Features

**Content & Discovery**
- Real-time movie/TV metadata synced from TMDB (trending, popular, new releases, upcoming)
- Dual-mode search: fast keyword search + AI-powered semantic search ("a mother protecting her child" finds relevant matches with zero keyword overlap)
- Browse by Movies / TV Shows
- Full content details: cast, crew, genres, ratings, backdrop/poster imagery

**Personalization & AI**
- Hybrid recommendation engine combining:
  - Content-based filtering (TF-IDF + cosine similarity)
  - Semantic similarity (sentence embeddings via fastembed/ONNX)
  - User preference modeling from ratings, favorites, and watch history
  - Real multi-signal trending score (popularity + rating + votes + recency + live app activity)
  - Recency and popularity signals
- Explainable recommendations — every suggestion includes a human-readable reason
- Cold-start handling for new users (falls back to popularity/rating-driven suggestions)

**User Features**
- Email/password authentication (Supabase Auth) with JWKS-verified JWTs
- Favorites, watchlist, ratings (add/update/remove)
- Personal analytics dashboard (genre breakdown chart, totals, average rating given)

**Admin**
- Admin-only dashboard: content/user totals, sync history, most-favorited content, popular searches
- Manual and scheduled (every 6 hours) content sync, with automatic model refit

**Engineering**
- Retry-with-backoff resilience for third-party API calls
- Full deduplication on every content sync (idempotent, safe to re-run)
- Row Level Security on every database table
- Real automated test suite (Pytest — unit + integration, 35 tests)

---

## Architecture

React + TypeScript + Tailwind CSS (frontend)
│
│ REST (JWT auth)
▼
FastAPI Backend ──────────────► TMDB API (via provider abstraction)
│ │
│ └──► ML Layer (TF-IDF, semantic embeddings, hybrid ranking)
▼
Supabase (PostgreSQL + Auth + RLS)


The frontend never talks to the database directly — every request goes through FastAPI, which validates the Supabase JWT (via JWKS signature verification) and then uses a service-role Supabase client for privileged reads/writes, with RLS as a defense-in-depth layer.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS, Framer Motion, Recharts, Axios |
| Backend | Python, FastAPI, Uvicorn, Pydantic |
| Database & Auth | Supabase (PostgreSQL, Auth, Row Level Security) |
| ML / NLP | scikit-learn (TF-IDF, cosine similarity), fastembed (ONNX-based sentence embeddings), pandas, NumPy |
| External Data | TMDB API (via a generic `ContentProvider` interface — swappable) |
| Scheduling | APScheduler (background sync jobs) |
| Testing | Pytest, FastAPI TestClient |

---

## Machine Learning Methodology

The recommendation engine is a **hybrid system**, not a single model:

1. **Content-based layer** — TF-IDF vectors over a combined "soup" of title, genres, overview, cast, and director; ranked by cosine similarity.
2. **Semantic layer** — dense sentence embeddings (via `fastembed`, using `BAAI/bge-small-en-v1.5`) enable meaning-based matching that goes beyond shared keywords.
3. **Personalization layer** — a weighted user preference vector built from ratings, favorites, and watch history, projected into the same vector space as the content/semantic models.
4. **Trending layer** — a real, multi-signal score (popularity + rating + vote count + release recency + actual recent app interactions) — not a re-labeled popularity number.
5. **Hybrid ranking** — a configurable weighted formula combines all signals into one final score, with an explanation generator producing human-readable reasoning per recommendation.

Known, documented limitation: the full similarity matrix approach is appropriate for the current catalog size; a larger catalog would need approximate nearest-neighbor search (e.g. `pgvector`), which the architecture is designed to support.

---

## Database Schema

21 normalized PostgreSQL tables, including: `profiles`, `content`, `genres`, `people`, `content_cast`, `content_crew`, `content_genres`, `content_availability`, `ott_platforms`, `ratings`, `reviews`, `favorites`, `watchlist`, `watch_history`, `search_history`, `user_preferences`, `user_interactions`, `recommendation_logs`, `content_embeddings`, `sync_logs`, `admin_logs`.

Full schema: [`supabase/migrations/001_initial_schema.sql`](./supabase/migrations/001_initial_schema.sql)

Every table has Row Level Security enabled — users can only access their own private data; content/reference tables are public-read; admin/log tables have zero public policies (service-role only).

---

## Installation

### Prerequisites
- Node.js 18+
- Python 3.10+ (tested on 3.14)
- A Supabase project
- A TMDB API key (free, personal-use tier)

### Backend setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
cp .env.example .env         # fill in your real values
```

Run the SQL schema in `supabase/migrations/001_initial_schema.sql` via Supabase's SQL Editor.

```bash
uvicorn app.main:app --reload
```

Backend runs at `http://127.0.0.1:8000` (docs at `/docs`).

### Frontend setup

```bash
cd frontend
npm install
cp .env.example .env         # set VITE_BACKEND_API_URL
npm run dev
```

Frontend runs at `http://localhost:5173`.

### Running tests

```bash
cd backend
pytest app/tests/ -v --cov=app
```

---

## Environment Variables

**Backend (`backend/.env`):**

ENVIRONMENT=
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
CONTENT_METADATA_API_KEY=
BACKEND_API_URL=
FRONTEND_URL=
MODEL_PATH=
EMBEDDING_MODEL_NAME=


**Frontend (`frontend/.env`):**

VITE_BACKEND_API_URL=


---

## API Overview

Full interactive documentation is auto-generated at `/docs` (Swagger UI) when the backend is running. Key endpoints:

| Endpoint | Description |
|---|---|
| `POST /api/auth/signup`, `/login` | Authentication |
| `GET /api/content/trending` | Live trending content (TMDB) |
| `GET /api/content/browse` | Browse synced catalog by type |
| `GET /api/content/search/keyword` | Keyword search |
| `GET /api/content/{id}` | Full content details (cast, crew, genres) |
| `GET /api/recommendations/user` | Personalized hybrid recommendations |
| `POST /api/recommendations/content` | "More like this" |
| `POST /api/recommendations/semantic-search` | Natural language search |
| `POST /api/favorites`, `/watchlist`, `/ratings` | User interactions |
| `GET /api/user/dashboard` | Personal analytics |
| `POST /api/admin/sync` | Trigger content sync (admin only) |
| `GET /api/admin/analytics` | System analytics (admin only) |

---

## Deployment Notes

This project's backend intentionally runs a full ML stack (embedding generation, TF-IDF, similarity computation) in-process at startup — a deliberate architectural choice to keep the recommendation engine genuinely real rather than a stub. This means it has a meaningfully larger memory footprint than a typical CRUD API, which is worth knowing when choosing hosting: free tiers capped at 512MB (common across Render, Railway, and similar platforms) are tight for this workload even after switching from `torch`/`sentence-transformers` to the lighter `fastembed`/ONNX runtime. A small paid tier (or a platform with a higher free-tier memory ceiling) is the most direct path to a smooth deployment; this is a normal, expected cost of hosting a real ML service, not a flaw in the architecture.

Recommended targets: **Render** or **Railway** (backend), **Vercel** (frontend, Vite/React).

---

## Future Improvements

- Approximate nearest-neighbor search (pgvector) for larger catalogs
- Recommendation diversity re-ranking (MMR) to reduce genre monotony
- Formal evaluation metrics (Precision@K, Recall@K, NDCG@K, coverage, diversity)
- Structured natural-language filter extraction ("comedy under 2 hours" → genre + runtime filters)
- Google OAuth login
- Move scheduled sync to a dedicated worker/cron process for reliable execution independent of web server uptime

---

## License

This project was built for educational/portfolio purposes.