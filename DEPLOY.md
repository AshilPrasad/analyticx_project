# Deploying analytix

This guide covers deploying **analytix** to production: a React frontend, FastAPI backend, and PostgreSQL database with the **pgvector** extension.

## Architecture

| Component | Recommended host | Notes |
|-----------|------------------|-------|
| Frontend | Render (static) or Vercel | Needs `VITE_API_URL` at **build** time |
| Backend | Render (Docker) | Reads `PORT` from the platform automatically |
| Database | Neon or Supabase | Must support **pgvector** |

```
Browser → Frontend (CDN) → Backend API → PostgreSQL + pgvector
                              ↓
                         Google Gemini (LLM + embeddings)
```

## Prerequisites

1. **Google Gemini API key** — [Google AI Studio](https://aistudio.google.com/app/apikey)
2. **PostgreSQL with pgvector** — e.g. [Neon](https://neon.tech) or [Supabase](https://supabase.com)
3. **Git repo** connected to Render and/or Vercel

---

## 1. Database (Neon example)

1. Create a Neon project and enable the **pgvector** extension:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

2. Copy the connection string and convert it for the backend:

```
postgresql+asyncpg://USER:PASSWORD@HOST/DBNAME?sslmode=require
```

Replace `postgresql://` with `postgresql+asyncpg://` if Neon gives you the plain form.

---

## 2. Backend on Render

### Option A — One-click Blueprint

1. Render Dashboard → **New** → **Blueprint**
2. Connect this repository
3. Render reads [`render.yaml`](render.yaml) and creates `analytix-api` + `analytix-web`
4. In the **analytix-api** service, set these env vars manually:
   - `DATABASE_URL` — your Neon/Supabase async URL
   - `GOOGLE_API_KEY` — your Gemini key
5. Redeploy both services after env vars are set

### Option B — Manual web service

1. **New → Web Service** → connect repo
2. **Root directory:** `backend`
3. **Runtime:** Docker
4. **Health check path:** `/health`
5. Set environment variables:

| Variable | Value |
|----------|-------|
| `APP_ENV` | `production` |
| `DATABASE_URL` | `postgresql+asyncpg://...` |
| `GOOGLE_API_KEY` | your Gemini key |
| `JWT_SECRET` | long random string (Render can generate) |
| `CORS_ORIGINS` | `https://your-frontend.onrender.com` |
| `LLM_MODEL` | `gemini-2.5-flash` |
| `EMBEDDING_MODEL` | `models/gemini-embedding-001` |
| `EMBEDDING_DIM` | `768` |

`PORT` is injected by Render — the Dockerfile already uses it.

---

## 3. Frontend

### Render (via Blueprint)

The blueprint sets `VITE_API_URL` from the API service URL automatically. Trigger a **manual redeploy** of the frontend after the API is live so the build picks up the correct URL.

### Vercel

1. Import the repo, set **Root Directory** to `frontend`
2. Add environment variable:
   - `VITE_API_URL` = `https://your-api.onrender.com`
3. Deploy

### Docker (self-hosted)

```bash
cd frontend
docker build --build-arg VITE_API_URL=https://your-api.onrender.com -t analytix-web .
docker run -p 8080:80 analytix-web
```

---

## 4. Environment variables reference

### Backend (`backend/.env`)

See [`backend/.env.example`](backend/.env.example).

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Async SQLAlchemy URL (`postgresql+asyncpg://...`) |
| `GOOGLE_API_KEY` | Yes* | Gemini key (*or set via in-app UI — see note below) |
| `JWT_SECRET` | Yes (prod) | Random secret for signing tokens |
| `APP_ENV` | Yes (prod) | Set to `production` |
| `CORS_ORIGINS` | Yes (prod) | Comma-separated frontend URLs |
| `PORT` | Auto | Set by Render/Railway; defaults to `8000` locally |

### Frontend (`frontend/.env`)

See [`frontend/.env.example`](frontend/.env.example).

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | Yes (prod) | Backend URL, e.g. `https://analytix-api.onrender.com` |

---

## 5. Post-deploy checklist

- [ ] `GET https://your-api/health` returns `"status": "healthy"` (database connected)
- [ ] Frontend loads and shows green connection dot
- [ ] Sign up / sign in works
- [ ] Upload a document and ask a question
- [ ] CORS: frontend origin is listed in backend `CORS_ORIGINS`

---

## Production notes

**Gemini API key in the UI:** The sidebar lets users save a Gemini key at runtime. On Render, the filesystem is ephemeral — keys saved only via the UI will **not survive redeploys**. Set `GOOGLE_API_KEY` as a platform env var for a stable production setup.

**Free tier cold starts:** Render free web services spin down after inactivity. The first request may take 30–60 seconds.

**Gemini rate limits:** Free-tier Gemini has request quotas. Heavy usage may return `429 RESOURCE_EXHAUSTED`.

**JWT secret:** Never use the default `change-me-in-production...` in production. Generate a 64+ character random string.

---

## Local development

```bash
# Database only (Docker)
docker compose up -d db

# Backend
cd backend
cp .env.example .env   # edit with your keys
pip install -r requirements.txt
python run.py

# Frontend
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open `http://localhost:5173`.
