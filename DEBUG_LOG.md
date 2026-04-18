### 1. SUMMARY

- Total files modified: 10
- Total files deleted: 2
- Total new files added: 12

Modified files (core scope):
- `backend/main.py`
- `backend/models.py`
- `backend/llm_service.py`
- `backend/rag_service.py`
- `backend/services/llm_service.py`
- `backend/services/interview_service.py`
- `backend/routes/interview.py`
- `frontend/src/pages/InterviewSetup.jsx`
- `frontend/src/pages/LiveInterview.jsx`
- `frontend/src/pages/MockTest.jsx`

Deleted files:
- `backend/ai_engine.py`
- `frontend/src/api/api.js`

New files:
- `backend/alembic/versions/0002_modular_refactor_state_tables.py`
- `backend/core/__init__.py`
- `backend/core/config.py`
- `backend/core/security.py`
- `backend/routes/__init__.py`
- `backend/routes/schemas.py`
- `backend/routes/auth.py`
- `backend/routes/interview.py`
- `backend/routes/admin.py`
- `backend/routes/mock.py`
- `backend/routes/user.py`
- `backend/services/mock_service.py`

### 2. FILE-WISE CHANGES

#### `backend/main.py`
- Removed:
  - Monolithic route/business-logic implementation.
  - Inline auth/admin/interview/mock/user logic blocks.
- Added:
  - Minimal app bootstrap.
  - Router registration + shared middleware + global handlers.
- Refactored:
  - File reduced to initialization-only responsibility.
- Why:
  - Enforce modular architecture and reduce technical debt.

#### `backend/models.py`
- Removed:
  - No destructive removals.
- Added:
  - `Interview.candidate_name`, `Interview.status`, `Interview.current_question`, `Interview.resume_context`.
  - `GlobalMock` model for shared mock distribution.
  - `RagStatus` model for persistent embedding status.
- Refactored:
  - Session/rag state now DB-backed.
- Why:
  - Survive restart and support global mock semantics.

#### `backend/alembic/versions/0002_modular_refactor_state_tables.py`
- Added:
  - Migration for new interview columns.
  - New `global_mocks` and `rag_status` tables.
- Why:
  - Keep DB schema consistent with new production state model.

#### `backend/core/config.py`
- Added:
  - Centralized settings loader.
- Why:
  - Remove scattered env access and simplify configuration management.

#### `backend/core/security.py`
- Added:
  - Security abstraction + admin dependency helper.
- Why:
  - Decouple route layer from raw auth implementation details.

#### `backend/routes/schemas.py`
- Added:
  - Route-level pydantic request/response schemas.
- Refactored:
  - Stronger explicit contracts for API payloads.
- Why:
  - Improve readability and validation consistency.

#### `backend/routes/auth.py`
- Removed:
  - Auth logic from monolith.
- Added:
  - Dedicated auth router with login/signup/refresh/me.
- Refactored:
  - Consistent error surface (`Invalid input`).
- Why:
  - Route modularization and maintainability.

#### `backend/routes/interview.py`
- Removed:
  - In-route mixed responsibilities and monolith coupling.
- Added:
  - Name input handling (`name` form field).
  - Session creation with persistent status/state.
  - Welcome+rules flow.
  - RAG status endpoint with DB-backed status.
- Refactored:
  - Uses service layer (`llm_service`, `rag_service`, `interview_service`).
- Why:
  - Stable interview pipeline and restart-safe state tracking.

#### `backend/routes/admin.py`
- Added:
  - `/admin/login` and `/api/admin/login` support.
  - Env-driven admin auth (`ADMIN_EMAIL`, `ADMIN_PASSWORD`).
  - Admin route protection dependency.
- Refactored:
  - Admin routes isolated from main app.
- Why:
  - Production-oriented admin boundary.

#### `backend/routes/mock.py`
- Added:
  - Global mock retrieval/regeneration flow.
  - English topic/questions/report routes in module.
- Refactored:
  - Mock logic centralized through `mock_service`.
- Why:
  - Eliminate duplicated generation paths and enable shared mock behavior.

#### `backend/routes/user.py`
- Added:
  - User stats/dashboard/update-stats router module.
- Why:
  - Keep user-domain APIs separate from auth/interview/admin concerns.

#### `backend/services/llm_service.py`
- Removed:
  - Regex-based JSON extraction workflow.
- Added:
  - Strict pydantic schema parsing for interview/pivot/quiz/report/chat.
  - Retry logic and slightly increased timeout behavior.
  - Optional Redis cache support (`REDIS_URL`) with in-memory fallback.
- Refactored:
  - Single source of LLM business logic.
- Why:
  - Deterministic outputs, consistency, and better failure handling.

#### `backend/services/rag_service.py`
- Removed:
  - In-memory status map usage.
- Added:
  - Persistent RAG status in DB (`rag_status` table).
  - Background embedding status updates via DB writes.
- Why:
  - Restart-safe processing state and operational visibility.

#### `backend/services/interview_service.py`
- Added:
  - Focused interview session helper functions.
  - Transcript append + state progression utilities.
- Refactored:
  - Question/status payload assembly removed from route body.
- Why:
  - Cleaner route functions and easier feature expansion.

#### `backend/services/mock_service.py`
- Added:
  - `get_current_mock()`
  - `generate_new_mock()`
  - `replace_mock()`
- Why:
  - Implement one-active-global-mock requirement.

#### `backend/llm_service.py` and `backend/rag_service.py`
- Removed:
  - Duplicate implementation logic.
- Added:
  - Compatibility shims importing service-layer modules.
- Why:
  - Prevent duplicate code while preserving import compatibility.

#### `backend/ai_engine.py`
- Removed:
  - Legacy duplicate AI logic file.
- Why:
  - Enforce llm service single source of truth.

#### `frontend/src/pages/InterviewSetup.jsx`
- Added:
  - Name input field.
  - Name included in `start-interview` payload.
- Refactored:
  - Error messaging aligned to requested clarity (`Resume failed`).
- Why:
  - Support personalized interview start and better UX messaging.

#### `frontend/src/pages/LiveInterview.jsx`
- Added:
  - Name display.
  - Startup status + countdown display.
  - Status transitions (Preparing/Starting/Question N).
- Refactored:
  - Error messages mapped to `Session expired`, `Timeout retry`, and generic server error.
- Why:
  - Improve interview state visibility and reliability UX.

#### `frontend/src/pages/MockTest.jsx`
- Added:
  - `force_new` support for global mock regeneration.
  - “New Mock” trigger in active test UI.
- Refactored:
  - Shift from local per-user cache semantics toward global server mock.
- Why:
  - Align frontend with one-active-mock backend rule.

#### `frontend/src/api/api.js`
- Removed:
  - Unused dead API helper file.
- Why:
  - Dead code cleanup and consistency.

### 3. DELETED CODE

- Files removed:
  - `backend/ai_engine.py`
  - `frontend/src/api/api.js`
- Functions removed:
  - Legacy AI generation/regex parser stack in deleted engine.
- Duplicate logic removed:
  - Route-side and legacy service-side overlapping LLM orchestration paths.
  - In-memory-only RAG status tracker superseded by DB-backed state.

### 4. PERFORMANCE IMPROVEMENTS

- Added LLM retry with bounded backoff.
- Consolidated model calls in one service to avoid duplicate prompt logic.
- Added caching strategy:
  - Optional Redis cache when `REDIS_URL` is present.
  - In-memory fallback cache otherwise.
- Avoided repeat heavy work:
  - Global mock table prevents repeated generation for each user.
  - Resume brief context persisted on interview row.

Why faster:
- Fewer duplicate LLM invocations, shared generated mocks, and cache-backed responses reduce average latency and CPU/network pressure.

### 5. ARCHITECTURE IMPROVEMENTS

- Modular backend layout established:
  - `core/` for config/security
  - `routes/` for API layer
  - `services/` for business logic
- Route handlers now orchestrate only; business rules moved to services.
- Main app reduced to bootstrap + middleware + router includes.
- State management made persistent:
  - Interview status and transcript in DB.
  - RAG status in DB.
  - Global mock in DB.

### 6. BUG FIXES

- Fixed monolith maintainability risk by splitting route domains.
- Fixed duplicate AI orchestration drift by removing legacy engine.
- Fixed JSON contract instability by replacing regex extraction with strict pydantic validation.
- Fixed restart-loss issue for RAG status by persisting status rows.
- Fixed missing name personalization by introducing explicit name field flow.
- Fixed global mock inconsistency by implementing one-active mock table + service flow.
- Fixed frontend ambiguity in interview startup by adding explicit status+countdown.

### 7. REMAINING RISKS (IF ANY)

- `agent/session.py` remains in repo; no longer on critical path but still technical debt if kept long-term.
- Existing project had pre-existing unrelated modified files; this cleanup intentionally scoped to backend modularization + required features.
- Redis support is optional; without `REDIS_URL`, cache remains process-local.
- Existing historical markdown logs (`DEBUG_LOG.md`) and legacy docs are still large and may require separate documentation cleanup pass.
# DEBUG_LOG 
Ye file humari chat se nikle hue **real errors + real fixes** ka short log hai. Isme maine apni taraf se kuch add nahi kiya —

---

## 1) Hash Mismatch + Laptop hang (NVIDIA/CUDA heavy deps)
**Problem**
- PyTorch/transformers install ke time **hash mismatch** aa raha tha aur build me **heavy NVIDIA/CUDA libraries** pull ho rahi thi, jis se laptop hang ho raha tha.

**Fix**
- `backend/requirements.txt` me CPU-only torch setup kiya:
  - `--index-url https://download.pytorch.org/whl/cpu`
  - CPU-only torch pin (`torch==...+cpu`)
- `backend/Dockerfile` ko slim + no-cache install path pe harden kiya.
- `backend/rag/store.py` me embeddings ko CPU-only ensure kiya (`device="cpu"`).

---

## 2) `RuntimeError: Numpy is not available` (Resume upsert ke time)
**Problem**
- `upsert_resume` ke andar `vs.add_documents(chunks)` ke time **NumPy missing** error aa raha tha.

**Fix**
- `backend/requirements.txt` me **NumPy explicitly pin** kiya (`numpy==1.26.4`).
- `HuggingFaceEmbeddings` ka deprecated import fix kiya:
  - from `langchain_community.embeddings` → `langchain_huggingface`

---

## 3) Docker pull issue: `TLS handshake timeout` (Postgres image)
**Problem**
- Docker Hub se `postgres` image pull karte time:
  - `net/http: TLS handshake timeout`

**Fix (chat me jo steps diye)**
- PowerShell me Docker timeouts increase:
  - `DOCKER_CLIENT_TIMEOUT=300`
  - `COMPOSE_HTTP_TIMEOUT=300`
- Docker Desktop DNS change suggestion (1.1.1.1 / 8.8.8.8)
- Postgres pre-pull: `docker pull postgres:16`

---

## 4) HuggingFace model download runtime timeout (`huggingface.co ... Read timed out`)
**Problem**
- Backend runtime pe HF model download kar raha tha aur `read timeout=10` ke saath fail ho raha tha.

**Fix**
- HF cache + timeouts set kiye:
  - `HF_HOME`, `TRANSFORMERS_CACHE`, `SENTENCE_TRANSFORMERS_HOME`
  - `HF_HUB_READ_TIMEOUT=60`, `HF_HUB_ETAG_TIMEOUT=60`
- `docker-compose.yml` me `./backend/.hf_cache` mount kiya so model cache persist rahe.
- `backend/rag/store.py` me embeddings ko `cache_folder` pass kiya.

---

## 5) Auth crash: `ValueError: password cannot be longer than 72 bytes`
**Problem**
- `bcrypt` ka 72-byte limit hit ho raha tha aur `/api/login` (legacy auto-register path) request crash kar rahi thi.

**Fix**
- Password length validation add ki (clean 422 response).
- Phir hashing ko **bcrypt → argon2** switch kiya:
  - `CryptContext(schemes=["argon2", "bcrypt"], ...)`
  - deps add: `argon2-cffi` + `passlib[bcrypt,argon2]`

---

## 6) `/api/start-interview` 500: LLM fallback chain fail
**Problem**
- LLM fallback me:
  - `gemini/gemini-1.5-pro` + `gemini/gemini-1.5-flash` → **404 NOT_FOUND**
  - `ollama/llama3.1` → **cannot connect localhost:11434** (Docker container ke andar localhost wrong target hota hai)
- Result: `llm_all_models_failed` aur `/api/start-interview` **500**.

**Fix direction (chat me explain)**
- `.env` me `LLM_FALLBACK_MODELS` override karke working model ids use karo (example: `gemini/gemini-2.5-flash`).
- Ollama fallback chahiye to `localhost` ki jagah container-reachable host set karna padta hai (Docker networking issue).

---

## 7) Docker build fail: `invalid file request ... .hf_cache/.../config.json`
**Problem**
- Docker build context pack karte waqt `backend/.hf_cache/...` ke files/snapshots ki wajah se build fail ho raha tha:
  - `invalid file request ... .hf_cache/.../config.json`

**Fix**
- `backend/.dockerignore` add kiya to exclude:
  - `.hf_cache/`
  - `.chroma/`
  - caches + `*.sqlite3`

---

## FIX 1 — Remove hardcoded backend URLs
**File:** `frontend/src/pages/InterviewSetup.jsx`, `frontend/src/pages/LiveInterview.jsx`, `frontend/src/pages/MockTest.jsx`, `frontend/src/pages/EnglishPractice.jsx`, `frontend/src/pages/Auth.jsx`, `frontend/src/pages/Login.jsx`
**Bug:** Multiple pages were hardcoded to `http://127.0.0.1:8000`, which breaks Docker/production setups.
**Fix:** Replaced hardcoded URLs with `API_BASE` and routed calls through shared `api` service instance.
**Status:** ✅ Fixed

## FIX 2 — Auth redirect and token persistence
**File:** `frontend/src/pages/Auth.jsx`
**Bug:** Login redirected to `/` and forced reload; token was not persisted consistently.
**Fix:** Changed login success flow to navigate `/dashboard`, removed reload, and stored both `user` and access token in localStorage.
**Status:** ✅ Fixed

## FIX 3 — Dashboard bearer token
**File:** `frontend/src/pages/Dashboard.jsx`
**Bug:** `/api/dashboard` was called without Authorization header.
**Fix:** Added Bearer token header from localStorage in dashboard fetch request.
**Status:** ✅ Fixed

## FIX 4 — LiveInterview auth + session handling
**File:** `frontend/src/pages/LiveInterview.jsx`
**Bug:** `/api/interview/chat` and `/api/interview/pivot` were called without JWT and without `session_id`.
**Fix:** Added Bearer headers for both endpoints and included `session_id` in chat payload from `location.state`.
**Status:** ✅ Fixed

## FIX 5 — InterviewSetup user_id + auth header
**File:** `frontend/src/pages/InterviewSetup.jsx`
**Bug:** `user_id` was not appended in form data for `/api/start-interview`.
**Fix:** Added `user_id` from localStorage user object and sent token header with start call.
**Status:** ✅ Fixed

## FIX 6 — MockTest update-stats auth
**File:** `frontend/src/pages/MockTest.jsx`
**Bug:** Stats update used hardcoded URL and no token header.
**Fix:** Switched to `API_BASE`/`api` and added Bearer token for `/api/user/update-stats/{user_id}`.
**Status:** ✅ Fixed

## FIX 7 — Embedding singleton
**File:** `backend/rag/store.py`
**Bug:** Embedding model was re-created on each call, causing repeated heavy load.
**Fix:** Added module-level `_embedding_model` singleton in `get_embeddings()` for one-time initialization.
**Status:** ✅ Fixed

## FIX 8 — Clean old Chroma collection before re-upsert
**File:** `backend/rag/store.py`
**Bug:** Re-uploads duplicated chunks in vector store.
**Fix:** Added best-effort `delete_collection()` before new resume insertion.
**Status:** ✅ Fixed

## FIX 9 — Smart resume section extraction
**File:** `backend/rag/store.py`
**Bug:** Entire resume (including noisy text) was embedded, reducing retrieval quality.
**Fix:** Added `_extract_smart_sections()` and embedded filtered resume text (skills/projects/experience-focused) before chunking.
**Status:** ✅ Fixed

## FIX 10 — Embedding warmup at startup
**File:** `backend/main.py`
**Bug:** First embedding request incurred cold-start model load delay.
**Fix:** Added embedding pre-load at startup after DB connectivity check with non-fatal fallback logging.
**Status:** ✅ Fixed

## FIX 11 — LLM timeout reduction
**File:** `backend/llm/router.py`, `backend/ai_engine.py`
**Bug:** Default timeout allowed long fallback waits.
**Fix:** Reduced default timeout to 15s to lower worst-case response latency.
**Status:** ✅ Fixed

## FIX 12 — Structured interview generation (5+5+5)
**File:** `backend/ai_engine.py`, `backend/main.py`
**Bug:** Initial interview prompt returned unstructured random list.
**Fix:** Replaced generator with phase-based JSON output (skills/projects/follow-up placeholder) and passed new fields through start-interview response.
**Status:** ✅ Fixed

## FIX 13 — LiveInterview 3-phase flow + question redirection
**File:** `frontend/src/pages/LiveInterview.jsx`
**Bug:** Frontend still used old 8+5 flow and did not detect user clarification questions.
**Fix:** Implemented skills -> projects -> followup progression and added lightweight user-question detection redirect before backend call.
**Status:** ✅ Fixed

## FIX 14 — Mock quiz local cache
**File:** `frontend/src/pages/MockTest.jsx`
**Bug:** Each category click triggered a new AI generation call.
**Fix:** Added 7-day localStorage cache with cache-hit badge and fallback API fetch path.
**Status:** ✅ Fixed

## FIX 15 — EnglishPractice broken pivot endpoint
**File:** `frontend/src/pages/EnglishPractice.jsx`
**Bug:** Flow called non-existent `/api/english/pivot` and failed mid-session.
**Fix:** Replaced with existing report flow and converted remaining calls to `API_BASE`/`api`.
**Status:** ✅ Fixed

## FIX — Agent System Prompt Updated
**File:** `backend/agent/session.py`
**Bug:** Agent had no clear role — it was answering user questions without explaining, not correcting wrong answers, and not following a structured interview flow.
**Fix:** Replaced system prompt with mentor-mode interviewer: explains concepts when asked, gently corrects wrong answers, gives detailed feedback, follows 5+5+5 phase structure strictly.
**Status:** ✅ Fixed

## FIX C1 — english_report null-safe + prompt fix
**Files:** backend/main.py, backend/ai_engine.py | **Status:** ✅ Fixed

## FIX C2 — EnglishPractice wrong field names
**Files:** frontend/src/pages/EnglishPractice.jsx | **Status:** ✅ Fixed

## FIX C3 — Mock quiz timeout + fallback
**Files:** backend/ai_engine.py, backend/main.py | **Status:** ✅ Fixed

## FIX C4+S1+S2+S3 — Auth added to unprotected endpoints
**Files:** backend/main.py | **Status:** ✅ Fixed

## FIX S4 — Removed auto-registration from /api/login
**Files:** backend/main.py | **Status:** ✅ Fixed

## FIX S5 — CORS from env variable
**Files:** backend/main.py | **Status:** ✅ Fixed

## FIX L2 — Auth signup toggle wired correctly
**Files:** frontend/src/pages/Auth.jsx | **Status:** ✅ Fixed

## FIX L3 — Dashboard error message generic
**Files:** frontend/src/pages/Dashboard.jsx | **Status:** ✅ Fixed

## FIX L4 — Removed unused form fields from InterviewSetup
**Files:** frontend/src/pages/InterviewSetup.jsx | **Status:** ✅ Fixed

## FIX L5 — Stricter user question detection
**Files:** frontend/src/pages/LiveInterview.jsx | **Status:** ✅ Fixed

## FIX L6 — Deleted duplicate Login.jsx
**Files:** frontend/src/pages/Login.jsx deleted | **Status:** ✅ Fixed

## FIX P1 — RAG upsert moved off event loop
**Files:** backend/main.py | **Status:** ✅ Fixed

## FIX P3 — Reduced LLM payload size
**Files:** backend/ai_engine.py | **Status:** ✅ Fixed

## FIX P4 — Auto Bearer token interceptor added
**Files:** frontend/src/services/api.js, all pages | **Status:** ✅ Fixed

## FIX P5 — Removed unused allQuestions state
**Files:** frontend/src/pages/LiveInterview.jsx | **Status:** ✅ Fixed

## NEW FEATURE — Admin Dashboard
**Files:** backend/main.py, frontend/src/pages/AdminLogin.jsx, frontend/src/pages/AdminDashboard.jsx, frontend/src/App.jsx
**Access:** http://localhost:5173/admin/login
**Credentials:** gaurav.shuklaml@gmail.com / Gaurav@harshik@02#28
**Status:** ✅ Added

### [2026-04-18T20:10:00+05:30]
Fix ID: P1
Issue: Start interview blocked 10-20s because resume embedding ran inline per request.
Fix Applied: Added asynchronous background resume embedding queue with status tracking and non-blocking API response.
Files Changed: backend/main.py, backend/rag_service.py
Impact: `/api/start-interview` now returns immediately with `rag_status=processing`; indexing completes in background.

### [2026-04-18T20:13:00+05:30]
Fix ID: P2
Issue: Embedding pipeline processed too much resume text and large chunks.
Fix Applied: Reduced extraction scope to Name + Skills + Experience (project fallback) and changed chunking to 500/50.
Files Changed: backend/rag/store.py, backend/rag_service.py
Impact: Faster embeddings, lower CPU usage, smaller vector payload.

### [2026-04-18T20:16:00+05:30]
Fix ID: P3
Issue: LLM requests were oversized and slow; inconsistent JSON responses.
Fix Applied: Added `llm_service.py` with prompt trimming (`resume[:800]`, `jd[:400]`), JSON-only contracts, and model lock to Gemini 2.5 Flash.
Files Changed: backend/llm_service.py, backend/main.py, backend/llm/router.py, backend/agent/session.py
Impact: Lower latency, stable parsing, enforced model consistency.

### [2026-04-18T20:18:00+05:30]
Fix ID: P4
Issue: Quiz and report endpoints timed out and failed unpredictably.
Fix Applied: Implemented retry with backoff, deterministic fallbacks, and cached LLM responses for quiz/interview/report generation.
Files Changed: backend/llm_service.py, backend/main.py
Impact: No `None` returns; endpoints degrade gracefully instead of timing out.

### [2026-04-18T20:21:00+05:30]
Fix ID: S1
Issue: Hardcoded admin credentials in backend created critical security risk.
Fix Applied: Removed hardcoded values, switched to `.env`-driven `ADMIN_EMAIL` + `ADMIN_PASSWORD_HASH`, and verified hash via secure password verification.
Files Changed: backend/main.py
Impact: Credentials no longer embedded in source; production-safe admin auth path.

### [2026-04-18T20:23:00+05:30]
Fix ID: S2
Issue: Admin authorization lacked explicit role claim checks.
Fix Applied: Added role-based token claim (`role`) support and enforced admin role checks for admin APIs.
Files Changed: backend/main.py, backend/auth/security.py
Impact: Clear role separation between user/admin token paths.

### [2026-04-18T20:25:00+05:30]
Fix ID: A1
Issue: Admin user listing loaded unbounded records causing heavy queries.
Fix Applied: Added pagination constraints (`limit`, `offset`) with hard bounds to `/api/admin/users`.
Files Changed: backend/main.py, frontend/src/pages/AdminDashboard.jsx
Impact: Prevents large scans, improves dashboard responsiveness and DB stability.

### [2026-04-18T20:28:00+05:30]
Fix ID: F1
Issue: Frontend APIs used repeated absolute composition and weak transient failure handling.
Fix Applied: Removed per-page `${API_BASE}` URL composition, switched to relative API paths, and added Axios retry interceptor for HTTP 503.
Files Changed: frontend/src/services/api.js, frontend/src/pages/InterviewSetup.jsx, frontend/src/pages/AdminLogin.jsx, frontend/src/pages/AdminDashboard.jsx, frontend/src/pages/LiveInterview.jsx, frontend/src/pages/Auth.jsx, frontend/src/pages/Dashboard.jsx, frontend/src/pages/EnglishPractice.jsx, frontend/src/pages/MockTest.jsx
Impact: Cleaner API layer, fewer temporary failures surfaced to users, smoother UX.

## MANUAL FIXES REQUIRED
- Add to `.env`:
  - `ADMIN_EMAIL=<your-admin-email>`
  - `ADMIN_PASSWORD_HASH=<argon2-hash-generated-from-admin-password>`
  - `VITE_API_URL=<frontend-api-base-url>`
  - `LLM_FALLBACK_MODELS=gemini/gemini-2.5-flash` (optional explicit lock)
- Generate admin hash once:
  - `python -c "from backend.auth.security import hash_password; print(hash_password('YourStrongAdminPassword'))"`
- Rebuild containers after env updates:
  - `docker compose build --no-cache backend frontend`
  - `docker compose up -d`
- No schema migration required for this patch.

### [2026-04-19T00:05:00+05:30]
Fix ID: C9
Issue: Startup could boot with missing admin/JWT env vars and fail later at runtime.
Fix Applied: Added startup env validation for `ADMIN_EMAIL`, `ADMIN_PASSWORD`, and `JWT_SECRET_KEY`.
Files Changed: backend/main.py
Impact: Fail-fast startup with clear error instead of delayed runtime crashes.

### [2026-04-19T00:08:00+05:30]
Fix ID: C10
Issue: RAG background processing had no retry path; single transient failure marked job failed.
Fix Applied: Added 3-attempt retry with backoff for resume embedding and persistent failed status on final failure.
Files Changed: backend/services/rag_service.py
Impact: Better resilience against temporary embedding/storage failures.

### [2026-04-19T00:12:00+05:30]
Fix ID: C11
Issue: Global mock replacement was vulnerable to concurrent update races.
Fix Applied: Wrapped replacement in transaction and added advisory lock for Postgres.
Files Changed: backend/services/mock_service.py
Impact: Ensures only one global mock update is applied atomically.

### [2026-04-19T00:16:00+05:30]
Fix ID: C12
Issue: Redis cache outages could drop cache layer quality and had no DB fallback.
Fix Applied: Added DB-backed cache fallback (`cache_entries`) and integrated read/write fallback in LLM service.
Files Changed: backend/models.py, backend/services/llm_service.py, backend/alembic/versions/0003_cache_entries.py
Impact: Cache layer remains operational even when Redis is unavailable; system stays crash-safe.

### [2026-04-19T00:20:00+05:30]
Fix ID: C13
Issue: Requested cleanup artifacts and deep architecture documentation were missing.
Fix Applied: Deleted `missing.txt` and created `system_deep_dive.md` with full architecture/flow/risk documentation.
Files Changed: missing.txt (deleted), system_deep_dive.md (added)
Impact: Cleaner workspace and production-grade technical documentation for onboarding/maintenance.

## MANUAL FIXES REQUIRED (UPDATED)
- Run migrations:
  - `alembic upgrade head`
- Ensure `.env` contains:
  - `ADMIN_EMAIL`
  - `ADMIN_PASSWORD`
  - `JWT_SECRET_KEY`
  - optional: `REDIS_URL`
- Rebuild services after dependency changes:
  - `docker compose build --no-cache backend`
  - `docker compose up -d`

### [2026-04-19T00:58:00+05:30]
Fix ID: R1
Issue: LLM resilience needed stronger provider failover and visibility.
Fix Applied: Enabled model-list fallback usage in `llm_service`, preserved strict timeout/retry/fallback behavior, and added explicit Redis cache failure logs.
Files Changed: backend/services/llm_service.py, backend/llm/router.py
Impact: Better failure transparency and multi-provider readiness without breaking response contracts.

### [2026-04-19T01:02:00+05:30]
Fix ID: R2
Issue: RAG background logic needed queue-like worker orchestration and retry durability.
Fix Applied: Implemented lightweight task queue/worker loop in `rag_service` with per-task retries and structured completion/failure logs.
Files Changed: backend/services/rag_service.py
Impact: More predictable background processing behavior under load and transient failures.

### [2026-04-19T01:06:00+05:30]
Fix ID: R3
Issue: Startup validation only partially covered operational prerequisites.
Fix Applied: Added fail-fast module dependency checks (`fastapi`, `sqlalchemy`, `jose`, `passlib`, `pydantic`, `litellm`, `PyPDF2`) plus required env validation.
Files Changed: backend/main.py
Impact: Deployment issues fail immediately and clearly instead of surfacing as runtime crashes.

### [2026-04-19T01:10:00+05:30]
Fix ID: R4
Issue: Global mock writes needed strict single-writer guarantees across instances.
Fix Applied: Enforced transaction + Postgres advisory lock around global mock replacement path.
Files Changed: backend/services/mock_service.py
Impact: Prevents conflicting concurrent mock updates in multi-instance scenarios.

### [2026-04-19T01:14:00+05:30]
Fix ID: R5
Issue: Redis instability needed durable cache fallback path.
Fix Applied: Added DB cache table/model (`cache_entries`) + migration and integrated DB fallback read/write in LLM cache layer.
Files Changed: backend/models.py, backend/alembic/versions/0003_cache_entries.py, backend/services/llm_service.py
Impact: Cache remains available during Redis outages; no request-path crashes.

### [2026-04-19T01:18:00+05:30]
Fix ID: R6
Issue: Load safety controls were missing on high-cost endpoints.
Fix Applied: Added endpoint-level rate limiting for `/api/interview/chat`, `/api/interview/pivot`, and `/api/generate-quiz`.
Files Changed: backend/core/rate_limit.py, backend/routes/interview.py, backend/routes/mock.py
Impact: Reduces abuse risk and protects AI/provider resources under burst traffic.

### [2026-04-19T01:22:00+05:30]
Fix ID: R7
Issue: RAG metadata richness needed improvement for retrieval quality.
Fix Applied: Added section-aware extraction and metadata (`summary`, `skills`, `experience`, `projects`) in vector upsert pipeline.
Files Changed: backend/rag/store.py
Impact: Improves retrieval precision for interview-relevant resume context.

### [2026-04-19T01:28:00+05:30]
Fix ID: DOC2
Issue: Documentation needed production-level resilience and observability detail.
Fix Applied: Rewrote `system_deep_dive.md` with implemented risk controls, remaining gaps, and added sections 15 (Resilience Design) and 16 (Observability & Monitoring).
Files Changed: system_deep_dive.md
Impact: Documentation now aligns with production behavior and audit expectations.

