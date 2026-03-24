# GitLab RAG

Chat assistant over GitLab handbook, product direction, and selected docs. It crawls public pages, chunks and embeds them into Chroma, retrieves with the user question, and answers with Gemini. Session context lives in Redis.

**Stack:** FastAPI, Chroma, Redis, Gemini (embeddings + chat), React (Vite).

## Run locally

1. `cp .env.example .env` and set **`GEMINI_API_KEY`** and **`GEMINI_CHAT_MODEL`** (see `.env.example` for the format; use any model id from [Google AI Studio](https://aistudio.google.com/), e.g. `models/gemini-3-flash-preview`).
2. Start API and Redis: `docker compose up --build`
3. Frontend: `cd frontend && npm install && npm run dev`

The app calls `http://localhost:8000` unless you set `VITE_API_URL` in `frontend/.env` (see `frontend/.env.example`).

## Deploy (Railway + Vercel)

**Costs:** Railway and Vercel both use **free tiers / trial credits** with limits. Watch usage in each dashboard so the demo stays within allowance.

### 1. API on Railway

1. Push this repo to **GitHub** (do not commit `.env`).
2. [Railway](https://railway.com) → **New project** → **Deploy from GitHub repo** → pick this repository.
3. Railway should detect the root **`Dockerfile`** and `railway.toml` (health check on `/health`). If it builds with Railpack instead, set the service **builder** to **Dockerfile** in the service settings, or rely on `railway.toml` in the repo.
4. **Add Redis:** In the project, **New** → **Database** → **Add Redis**. Open the Redis service → **Variables** and copy the connection URL (often named `REDIS_URL` or similar).
5. **Add a volume** for Chroma: open your **web** service → **Settings** → **Volumes** → add a volume, **mount path** ` /app/chroma_db ` (same path as in Docker).
6. **Environment variables** on the **web** service (Variables tab):

| Variable | Value |
|----------|--------|
| `GEMINI_API_KEY` | From [Google AI Studio](https://aistudio.google.com/apikey) |
| `GEMINI_CHAT_MODEL` | Required. Same as local, e.g. `models/gemini-3-flash-preview` |
| `REDIS_URL` | Paste the Redis URL from step 4 |
| `CHROMA_PERSIST_DIR` | `/app/chroma_db` |
| `LOG_LEVEL` | `INFO` |
| `CORS_ORIGINS` | Leave empty at first, or set to your Vercel URL after step 2 (e.g. `https://your-app.vercel.app`) |

7. **Generate a public URL:** Web service → **Settings** → **Networking** → **Generate domain**. Copy the HTTPS URL (no trailing slash). Check `https://<your-url>/health` returns 200.

### 2. Frontend on Vercel

1. [Vercel](https://vercel.com) → **Add New Project** → import the **same** GitHub repo.
2. **Root Directory:** `frontend`
3. Build: `npm run build`, output: `dist` (defaults for Vite).
4. **Environment variable:** `VITE_API_URL` = your Railway API URL (e.g. `https://xxx.up.railway.app`), **no trailing slash**.
5. Deploy. Your **HR-facing link** is the Vercel URL (e.g. `https://xxx.vercel.app`).

### 3. CORS (recommended)

After you have the Vercel URL, set **`CORS_ORIGINS`** on the Railway web service to that exact origin (e.g. `https://your-app.vercel.app`), redeploy, and test chat again.

### 4. First run

Open the Vercel app → **Sync Docs** once so ingestion runs and Chroma fills. Ingestion can take a while depending on Gemini quota.

## Ops

- Rotate `GEMINI_API_KEY` in Railway and redeploy.
- **Sync Docs** re-runs ingestion; existing chunks are skipped when IDs match.
- Clearing the Chroma volume forces a full re-embed (costly on API quota).

## Optional: Render

`render.yaml` is an optional blueprint for [Render.com](https://render.com) if you prefer that host instead of Railway.
