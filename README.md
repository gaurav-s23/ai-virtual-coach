# AI Virtual Interview Coach

A full-stack AI-powered interview preparation and simulation platform - personalized, adaptive, and resume-grounded.

## What Is This

AI Virtual Interview Coach is a complete interview readiness environment for students, job seekers, and placement coordinators. Candidates can sign up, upload a resume, enter a structured AI-driven interview simulation, receive intelligent feedback and scoring, and track their progress through a personal dashboard.

The system grounds every interview prompt in your actual resume and job description using RAG (Retrieval-Augmented Generation), making each session uniquely tailored - not generic.

**Platform Focus:** This system specializes in Text-to-Text (Chat) and Vision-based interview preparation, excluding audio processing to ensure focused development and deployment.

**Who it's for:**
- Students preparing for campus placements and internships
- Job seekers practicing technical and behavioral rounds
- Placement officers / program coordinators (admin view)

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19 + Vite + React Router + Tailwind CSS |
| **Backend API** | FastAPI + Pydantic + Uvicorn |
| **AI / ML** | PyTorch + OpenCV + LangChain + ChromaDB |
| **Database** | PostgreSQL + SQLAlchemy + Alembic |
| **Authentication** | JWT + Argon2/bcrypt |
| **Real-time** | WebSocket + Browser APIs |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+ and npm 10+
- Docker + Docker Compose (recommended)

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

# OPTIONAL
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
| API Docs | http://localhost:8000/docs |

### 3. Run Manually

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

## For detailed technical logs, architecture, and bug tracking, see [TECHNICAL_DOCS.md](./TECHNICAL_DOCS.md)