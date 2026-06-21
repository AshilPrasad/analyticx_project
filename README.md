# analytix

RAG-powered document Q&A — upload PDFs/text, ask questions, and get answers grounded in your knowledge base.

**Stack:** React · FastAPI · PostgreSQL/pgvector · Google Gemini (LLM + embeddings)

## Quick start (local)

```bash
# 1. Start PostgreSQL with pgvector
docker compose up -d db

# 2. Backend
cd backend
cp .env.example .env          # add GOOGLE_API_KEY + JWT_SECRET
pip install -r requirements.txt
python run.py                 # http://localhost:8000

# 3. Frontend
cd frontend
cp .env.example .env
npm install
npm run dev                   # http://localhost:5173
```

## Deploy to production

See **[DEPLOY.md](DEPLOY.md)** for Render, Vercel, Neon/Supabase, and environment variable setup.

One-click option: connect this repo to [Render Blueprint](https://render.com/docs/blueprint-spec) using [`render.yaml`](render.yaml).

## Features

- ChatGPT-style UI with sidebar chat history (90-day retention)
- User signup / signin with JWT auth and per-user data isolation
- Document upload (PDF, TXT) with semantic search
- In-app Gemini API key configuration
- Graceful degradation when the database is unavailable (dev mode)

## API docs

With the backend running: [http://localhost:8000/docs](http://localhost:8000/docs)
