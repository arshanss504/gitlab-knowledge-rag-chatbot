# GitLab RAG

Chat assistant over GitLab handbook, product direction, and selected docs. It crawls public pages, chunks and embeds them into Chroma, retrieves with the user question, and answers with Gemini. Session context lives in Redis.

**Stack:** FastAPI, Chroma, Redis, Gemini (embeddings + chat), React (Vite).

## Run locally

1. `cp .env.example .env` and set `GEMINI_API_KEY` (from [Google AI Studio](https://aistudio.google.com/apikey)).
2. Start API and Redis: `docker compose up --build`
3. Frontend: `cd frontend && npm install && npm run dev`

The app calls `http://localhost:8000` unless you set `VITE_API_URL` in `frontend/.env` (see `frontend/.env.example`).

## Deploy (Render + Vercel)

**API (Render):** Docker build from repo root, port 8000. Mount a disk at `/app/chroma_db` and set `CHROMA_PERSIST_DIR=/app/chroma_db`. Add Redis and set `REDIS_URL` to its internal URL.

| Variable | Notes |
|----------|--------|
| `GEMINI_API_KEY` | Required |
| `CHROMA_PERSIST_DIR` | e.g. `/app/chroma_db` |
| `REDIS_URL` | Redis connection string |
| `CORS_ORIGINS` | Your Vercel URL(s), comma-separated |
| `LOG_LEVEL` | e.g. `INFO` |

**Frontend (Vercel):** Root directory `frontend`, build `npm run build`, output `dist`. Set `VITE_API_URL` to your Render URL (no trailing slash).

After deploy, use **Sync Docs** once in the UI so the vector store is populated. Confirm `GET /health` on the API returns 200.

## Ops

- Rotate `GEMINI_API_KEY` in Render and redeploy.
- **Sync Docs** re-runs ingestion; existing chunks are skipped when IDs match.
- Clearing Chroma data forces a full re-embed (costly on API quota).
