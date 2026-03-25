# GitLab RAG

Chat assistant over GitLab handbook, product direction, and selected docs. It crawls public pages, chunks and embeds them into Chroma, retrieves with the user question, and answers with Gemini. Session context lives in Redis.

**Stack:** FastAPI, Chroma, Redis, Gemini (embeddings + chat), React (Vite).

## Run locally

1. `cp .env.example .env` and set **`GEMINI_API_KEY`** and **`GEMINI_CHAT_MODEL`** (e.g. `models/gemini-3-flash-preview`).
2. Start API and Redis: `docker compose up --build`
3. Frontend: `cd frontend && npm install && npm run dev`

The app calls `http://localhost:8000` unless you set `VITE_API_URL`

## Ops

- Rotate `GEMINI_API_KEY` in test and redeploy.
- **Sync Docs** re-runs ingestion; existing chunks are skipped when IDs match.
- Clearing the Chroma volume forces a full re-embed (costly on API quota).
