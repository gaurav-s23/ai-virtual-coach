## AI Virtual Coach

Full‑stack interview practice app with a FastAPI backend and a React frontend. It supports resume‑grounded interviewing (RAG), persistent interview history, and production-style backend concerns (JWT auth, migrations, rate limiting).

### What’s in here
- **Backend**: FastAPI, SQLAlchemy, Alembic, JWT auth (access + refresh), SlowAPI rate limiting
- **RAG**: ChromaDB + local CPU embeddings via `sentence-transformers/all-MiniLM-L6-v2`
- **LLM routing**: LiteLLM-backed fallback list (configurable via env)
- **Frontend**: React + Vite, served via Nginx in Docker

---

## Quick start (Docker)

### 1) Configure environment
Create `.env` in the repo root (don’t commit it). Use `.env.example` as a template.

Minimum you’ll need:
- **`GOOGLE_API_KEY`**: used for Gemini via LiteLLM
- **`JWT_SECRET_KEY`**: signing key for JWT access tokens

### 2) Build + run

```bash
docker compose up --build
```

Open:
- **Frontend**: `http://localhost:5173`
- **Backend**: `http://localhost:8000`
- **API docs**: `http://localhost:8000/docs`

---

## Backend details

### Authentication
- Password hashing uses **Argon2** (bcrypt kept for verifying legacy hashes).
- Access token is a JWT; refresh tokens are opaque strings stored **hashed** in the DB.

Auth endpoints:
- `POST /api/auth/signup`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `GET /api/auth/me`

Legacy compatibility:
- `POST /api/login` still exists (legacy client support) and returns tokens.

### Rate limiting
SlowAPI is enabled by default and can be toggled via:
- `RATELIMIT_ENABLED=true|false`

### Migrations
This repo uses Alembic. In Docker, migrations run via the `migration` service before the backend starts.

Local (from `backend/`):

```bash
alembic upgrade head
```

---

## RAG (resume ingestion)
On `POST /api/start-interview`, the backend:
1. Loads the uploaded PDF via `PyPDFLoader`
2. Splits it into chunks
3. Embeds chunks using **local CPU embeddings** (`HF_EMBEDDING_MODEL`, default `sentence-transformers/all-MiniLM-L6-v2`)
4. Stores vectors in **ChromaDB** (persisted to `./backend/.chroma` when running via Docker)

---

## API (most used)
- `POST /api/start-interview` (multipart: `resume`, `jd`, `role`, `user_id`)
- `POST /api/interview/chat` (JWT protected; persists transcript)
- `GET /api/interview/{session_id}/history` (JWT protected)
- `GET /api/dashboard?user_id=...` (JWT protected)

---

## Configuration notes

### LLM fallback list
Set the model priority list using:
- `LLM_FALLBACK_MODELS=...`

Example:

```env
LLM_FALLBACK_MODELS=gemini/gemini-2.5-flash,gemini/gemini-2.5-pro
```

### HuggingFace cache
In Docker, HF cache is mounted so embedding models don’t re-download on every run:
- `./backend/.hf_cache:/app/.hf_cache`


