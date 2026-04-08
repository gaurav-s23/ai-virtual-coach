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

