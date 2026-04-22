# 🤖 AI Virtual Interview Coach

> **A full-stack AI-powered interview preparation and simulation platform** — personalized, adaptive, and resume-grounded.

---

## 📌 What Is This?

AI Virtual Interview Coach is a complete interview readiness environment for students, job seekers, and placement coordinators. Candidates can sign up, upload a resume, enter a structured AI-driven interview simulation, receive intelligent feedback and scoring, and track their progress through a personal dashboard.

The system grounds every interview prompt in your actual resume and job description using RAG (Retrieval-Augmented Generation), making each session uniquely tailored — not generic.

**Platform Focus:** This system specializes in **Text-to-Text (Chat) and Vision-based** interview preparation, excluding audio processing to ensure focused development and deployment.

**Who it's for:**
- 🎓 Students preparing for campus placements and internships
- 💼 Job seekers practicing technical and behavioral rounds
- 🏫 Placement officers / program coordinators (admin view)

---

## ✨ Features at a Glance

| Feature | Status |
|---|---|
| JWT Auth (signup / login / refresh token rotation) | Working |
| Resume Upload & PDF Parsing | Working |
| RAG — Resume Embedded into Vector DB (ChromaDB) | Working |
| 5-Step Interview Setup Wizard | Working |
| Live Interview (skill → project → pivot phases) | Working |
| AI Question Generation via Gemini (LiteLLM fallback) | Working |
| Text-to-Speech (Browser API) | Working |
| Speech-to-Text (Browser Web Speech API) | Working |
| Interview Pivot / Deep-Dive Followups | Working |
| Answer Relevance Verifier (sentence-transformers) | Working |
| Answer Quality Scorer (cross-encoder ML model) | Working |
| Vision Analysis (Eye-contact/Engagement) | Working |
| Confidence Scoring (Text-based Delivery) | Working |
| Mock Test (MCQ with timer) | Working |
| English Fluency Practice | Working |
| Performance Dashboard (readiness score, streak) | Working |
| Proctoring (tab switch, timing detection) | Working |
| WebSocket Real-time Feedback | Working |
| Admin Dashboard | Working |
| LLM Response Caching (DB-backed + optional Redis) | Working |
| Rate Limiting (SlowAPI) | Working |
| LangChain Agent (tool-augmented coaching) | Working |
| Vision System (OpenCV + PyTorch) | Working |
| Confidence Analytics (Neural Network) | Working |
| DSA Coding Challenge Section | Working |
| Discussion-Based Interview Logic | Working |

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19 + Vite + React Router + Tailwind CSS |
| **Backend API** | FastAPI + Pydantic + Uvicorn |
| **ORM / DB** | SQLAlchemy + Alembic + PostgreSQL (Docker) / SQLite fallback |
| **Auth** | JWT access tokens + Argon2/bcrypt hashed refresh tokens |
| **AI / LLM** | LiteLLM + LangChain (Gemini via Google API) |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` (local CPU) |
| **Vector Store** | ChromaDB (persistent per-user resume index) |
| **Deep Learning** | sentence-transformers, cross-encoder, PyTorch, OpenCV |
| **Real-time** | Browser Web Speech APIs + FastAPI WebSocket |
| **Rate Limiting** | SlowAPI + in-memory request buckets |
| **Caching** | In-memory + DB `cache_entries` table + optional Redis |

---

## 🗂️ Project Structure

```
project-root/
├── docker-compose.yml
├── .env.example
├── README.md
│
├── backend/
│   ├── main.py                    # FastAPI app entry, WebSocket, startup hooks
│   ├── database.py                # SQLAlchemy engine + session
│   ├── models.py                  # ORM models (users, sessions, transcripts, cache…)
│   ├── requirements.txt
│   │
│   ├── core/
│   │   ├── config.py              # Settings + env validation
│   │   ├── rate_limit.py          # In-memory request bucket limiter
│   │   └── security.py            # JWT helpers (issue, verify, refresh rotation)
│   │
│   ├── auth/
│   │   └── security.py            # Password hash + verify (Argon2/bcrypt)
│   │
│   ├── routes/
│   │   ├── auth.py                # /api/auth/* + legacy /api/login
│   │   ├── interview.py           # /api/start-interview, /api/interview/*
│   │   ├── mock.py                # /api/generate-quiz, /api/english/*
│   │   ├── user.py                # /api/user/*, /api/dashboard
│   │   ├── admin.py               # /api/admin/*
│   │   ├── proctor.py             # /api/proctor/*
│   │   └── schemas.py             # Pydantic request/response schemas
│   │
│   ├── services/
│   │   ├── llm_service.py         # LiteLLM orchestration + caching
│   │   ├── rag_service.py         # Resume chunking + ChromaDB upsert + status
│   │   ├── interview_service.py   # Interview session persistence helpers
│   │   ├── mock_service.py        # Quiz generation helpers
│   │   ├── answer_verifier.py     # Semantic relevance scoring (MiniLM)
│   │   ├── scoring_service.py     # Quality scoring (cross-encoder)
│   │   ├── audio_features.py     # librosa MFCC / confidence analyzer
│   │   ├── vision_service.py      # OpenCV + PyTorch vision analysis
│   │   ├── confidence_service.py  # PyTorch confidence scoring
│   │   ├── discussion_service.py  # Discussion-based interview logic
│   │   ├── coding_service.py      # DSA coding challenge generation
│   │
│   ├── llm/
│   │   └── router.py              # LiteLLM fallback model routing
│   │
│   ├── rag/
│   │   └── store.py               # ChromaDB read/write wrappers
│   │
│   ├── agent/
│   │   ├── session.py             # LangChain AgentExecutor session manager
│   │   ├── tools.py               # Resume search, scorer, feedback tools
│   │   └── policy.py              # Agent guardrails and policy config
│   │
│   ├── alembic/versions/
│   │   ├── 0001_initial_schema.py
│   │   ├── 0002_modular_refactor_state_tables.py
│   │   └── 0003_cache_entries.py
│   │
│   └── test_api.py / test_auth_and_persistence.py / test_rag_and_llm.py
│
└── frontend/
    ├── package.json
    └── src/
        ├── main.jsx               # React entry + ErrorBoundary
        ├── App.jsx                # Router + auth guards
        ├── services/api.js        # Axios wrappers for all API calls
        │
        ├── pages/
        │   ├── Home.jsx
        │   ├── Auth.jsx           # Login / Signup
        │   ├── InterviewSetup.jsx # 5-step wizard
        │   ├── LiveInterview.jsx  # Main interview HUD
        │   ├── Dashboard.jsx      # Stats, skill bars, streak
        │   ├── MockTest.jsx       # MCQ timer exam
        │   ├── EnglishPractice.jsx
        │   ├── AdminLogin.jsx
        │   ├── AdminDashboard.jsx
        │   └── Evaluation.jsx     # (currently unrouted)
        │
        └── components/
            ├── ErrorBoundary.jsx
            ├── ErrorState.jsx
            ├── LoadingSpinner.jsx
            ├── SkillBars.jsx
            └── StatCard.jsx
```

---

## 🚀 Quick Start

### Prerequisites

- Python **3.11+**
- Node.js **20+** and npm **10+**
- Docker + Docker Compose *(recommended)*
- PostgreSQL 16 *(only if running manually without Docker)*

### 1. Clone & Configure

```bash
git clone <your-repo-url>
cd <project-root>
cp .env.example .env
```

Fill in the required values in `.env`:

```env
# REQUIRED
GOOGLE_API_KEY=your_gemini_api_key
JWT_SECRET_KEY=your_very_secret_key_here
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your_admin_password

# OPTIONAL (defaults shown)
DATABASE_URL=                    # Leave empty for SQLite fallback
REDIS_URL=                       # Leave empty to skip Redis
CORS_ORIGINS=http://localhost:5173
```

### 2. Run with Docker (Recommended)

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

### 3. Run Manually (Without Docker)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn backend.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## 🔑 Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_API_KEY` | **Yes** | — | Gemini LLM key; missing breaks all AI generation |
| `JWT_SECRET_KEY` | **Yes** | — | JWT signing secret; app won't start without it |
| `ADMIN_EMAIL` | **Yes** | — | Admin account email |
| `ADMIN_PASSWORD` | **Yes** | — | Admin account password |
| `DATABASE_URL` | Prod only | SQLite fallback | SQLAlchemy connection URL |
| `REDIS_URL` | Optional | — | Enables Redis cache layer |
| `CORS_ORIGINS` | Optional | localhost list | Comma-separated allowed origins |
| `VITE_API_URL` | Optional | — | Frontend API base URL override |
| `CHROMA_DIR` | Optional | `./backend/.chroma` | ChromaDB persistence path |
| `HF_EMBEDDING_MODEL` | Optional | `all-MiniLM-L6-v2` | Local embedding model |
| `LLM_FALLBACK_MODELS` | Optional | internal defaults | Ordered fallback chain for text generation |
| `RATELIMIT_ENABLED` | Optional | `true` | Toggle route throttling |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Optional | `30` | JWT access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Optional | `7` | Refresh token TTL |

---

## 📡 API Reference (Summary)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/signup` | No | Register new user |
| `POST` | `/api/auth/login` | No | Login, receive token pair |
| `POST` | `/api/auth/refresh` | No | Rotate refresh token |
| `GET` | `/api/auth/me` | ✅ | Get current user |
| `POST` | `/api/start-interview` | ✅ | Upload resume, begin session |
| `POST` | `/api/interview/chat` | ✅ | Send answer, get AI response + scores |
| `POST` | `/api/interview/pivot` | ✅ | Trigger deep-dive follow-up phase |
| `GET` | `/api/interview/{session_id}/history` | ✅ | Fetch transcript |
| `GET` | `/api/interview/rag-status` | ✅ | Check resume embedding status |
| `POST` | `/api/interview/analyze-audio` | ⚠️ No auth | Audio features (MFCC, confidence) |
| `POST` | `/api/generate-quiz` | ✅ | Generate MCQ quiz by category |
| `GET` | `/api/english/topic` | ✅ | Get fluency practice topic |
| `POST` | `/api/english/questions` | ✅ | Generate English practice questions |
| `POST` | `/api/english/report` | ✅ | Generate fluency report |
| `GET` | `/api/dashboard` | ✅ | Fetch user stats + skill data |
| `POST` | `/api/user/update-stats/{user_id}` | ✅ | Update readiness score |
| `POST` | `/api/admin/login` | No | Admin authentication |
| `GET` | `/api/admin/stats` | Admin | Platform-wide stats |
| `GET` | `/api/admin/users` | Admin | Paginated user list |
| `POST` | `/api/proctor/log` | ⚠️ No auth | Log proctoring event |
| `GET` | `/api/proctor/report/{session_id}` | ⚠️ No auth | Get integrity report |
| `WS` | `/ws/interview/{session_id}` | ⚠️ No auth | Real-time feedback channel |

---

## 🧠 Interview Flow

```
Interview Setup (5 steps)
        ↓
  POST /api/start-interview
        ↓
  ┌─────────────────┐
  │   Skill Phase   │ ← AI asks skill questions from resume context
  └────────┬────────┘
           ↓ (complete)
  ┌─────────────────┐
  │  Project Phase  │ ← AI probes project-specific experience
  └────────┬────────┘
           ↓ (complete)
  ┌─────────────────┐
  │  Pivot Phase    │ ← POST /api/interview/pivot → deep-dive follow-ups
  └────────┬────────┘
           ↓ (complete)
  ┌─────────────────┐
  │ Discussion-Based Logic │ ← Discussion-based analysis and follow-up generation
  └────────┬────────┘
           ↓ (complete)
      Dashboard
  (readiness score, skill bars, streak updated)
```

Each chat turn runs:
1. **Answer Relevance Check** — semantic similarity via MiniLM
2. **Answer Quality Score** — cross-encoder ML signal
3. **Discussion-Based Analysis** — Topic mastery detection and follow-up generation
4. **Vision Analysis** - Real-time camera feed for eye-contact and engagement detection
5. **Confidence Scoring** - Text-based delivery confidence analysis using PyTorch
6. **Proctoring Check** — timing anomaly detection
7. **LLM Reply Generation** — Gemini via LiteLLM with fallback
8. **Cache Write** — DB-backed cache_entries for repeat queries

---

## 🐛 Known Bugs

| # | Severity | File | Problem |
|---|---|---|---|
| 1 | 🔵 Medium | `Home.jsx` | `user.email.split` crashes on malformed localStorage object |
| 2 | 🟡 High | `EnglishPractice.jsx` | `phase` state unused — deep-dive transition logic incomplete |
| 3 | 🔵 Medium | `Evaluation.jsx` | Page not registered in `App.jsx` router (unreachable) |
| 4 | 🟡 High | `Dashboard.jsx` | Dynamic Tailwind class strings get purged in production build |
| 5 | 🔴 Critical | `proctor.py` | Proctoring endpoints have **no authentication guard** |
| 6 | 🔴 Critical | `main.py` (WebSocket) | WebSocket is **unauthenticated** and only echoes, no actual AI pipeline |
| 7 | 🟡 High | `interview.py` | Audio analysis endpoint has **no auth** |
| 8 | 🔵 Medium | `audio_features.py` | WPM estimate uses crude sample-length heuristic (not real segmentation) |
| 9 | 🟡 High | `LiveInterview.jsx` | Hard redirect on missing route state — no session recovery endpoint |
| 10 | 🟡 High | `Auth.jsx` | Uses legacy `/api/login` instead of canonical `/api/auth/login` |
| 11 | 🔵 Medium | `MockTest.jsx` | Vague alert on empty/invalid quiz payload from backend |
| 12 | 🔵 Medium | `llm_service.py` | Cache key collision possible on long truncated content |
| 13 | 🟡 High | `scoring_service.py` | Cold-start model load blocks first inference — no background warmup |
| 14 | 🔴 Critical | `test_api.py` | Monkeypatched symbols point to stale module paths after refactor |
| 15 | 🔵 Medium | `AdminDashboard.jsx` | Admin auth relies on localStorage only — no expiry/route guard |

---

## 🔧 Common Setup Errors

| Error | Cause | Fix |
|---|---|---|
| `Missing required env: JWT_SECRET_KEY` | Not set in `.env` | Add `JWT_SECRET_KEY` |
| `Database connectivity check failed` | DB not reachable | Verify `DATABASE_URL` and DB container |
| `Session expired` during chat | Stale `session_id` | Restart from setup wizard |
| `401` on protected routes | Missing/expired token | Login again, check `Authorization` header |
| `429 Too Many Requests` | Rate limit hit | Wait reset window or tune `RATELIMIT_ENABLED` |
| Empty quiz / server error | Missing `GOOGLE_API_KEY` | Verify Gemini API key in `.env` |
| STT not working | Unsupported browser | Use Chromium-based browser |
| CORS blocked | Origin not in allowlist | Add frontend URL to `CORS_ORIGINS` |
| Audio analyze fails | Missing librosa/soundfile | Reinstall backend deps including audio libs |

---

## 🧪 Running Tests

```bash
cd backend

# Auth + persistence tests
pytest test_auth_and_persistence.py -v

# Full API flow tests
pytest test_api.py -v

# RAG + LLM pipeline tests
pytest test_rag_and_llm.py -v
```

> ⚠️ **Note:** `test_api.py` has stale monkeypatch paths (Bug #14). Some tests may fail until the import paths are corrected after the last refactor.

---

## 📈 Scaling Notes

| Scale | Key Changes Needed |
|---|---|
| **~100 users** | Add auth to proctor/audio routes; switch fully to Postgres; warm ML models at startup |
| **~10k users** | Redis for rate limits + session state; Celery/RQ for embedding tasks; structured logging + tracing |
| **~1M users** | Microservices split; Kubernetes; sharded Postgres + read replicas; dedicated model-serving (Triton/TorchServe) |

---

## 🔐 Security Considerations

- ⚠️ `/api/proctor/*` and `/api/interview/analyze-audio` currently have **no authentication**
- ⚠️ WebSocket `/ws/interview/{session_id}` has **no token validation**
- ⚠️ Admin auth is checked only client-side in `AdminDashboard.jsx`
- Recommended: add `Depends(get_current_user)` to all unguarded routes before production deploy
- Recommended: implement account lockout / brute-force protection on login

---

## 🗺️ Roadmap

**Next to build:**
1. Auth guard on proctor + WebSocket endpoints
2. Durable background job queue (Celery/RQ) for RAG + scoring
3. Session bootstrap endpoint for `/live-interview` direct URL reload recovery
4. Deterministic interview report persistence per session
5. Unified frontend auth context with automatic token refresh

**Nice-to-haves:**
- Interview replay timeline with transcript + score overlays
- JD-resume skill gap heatmap
- Multi-language interview mode
- Email / post-session report export

---

## 📖 Glossary

| Term | Meaning |
|---|---|
| **RAG** | Retrieval-Augmented Generation — LLM responses grounded in retrieved resume chunks |
| **ChromaDB** | Vector database for semantic resume search |
| **LiteLLM** | Unified multi-provider LLM interface with fallback routing |
| **Pivot Phase** | Deep-dive follow-up interview stage after main phases |
| **Readiness Score** | Numeric signal of candidate interview preparedness |
| **MFCC** | Mel-frequency cepstral coefficients — audio feature for speech analysis |
| **Cross-encoder** | ML model for fine-grained answer quality scoring |
| **Alembic** | SQLAlchemy migration tool for schema evolution |
| **Cold Start** | Initial high latency when loading ML model into memory for first time |

---

## 📄 License

*Specify your license here.*

---

*Built with ❤️ for serious interview prep.*