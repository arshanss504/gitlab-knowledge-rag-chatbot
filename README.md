# GitLab RAG Chatbot

A Retrieval-Augmented Generation (RAG) chatbot for GitLab Handbook, docs, and direction content.

## Repository layout

```
gitlab-rag/
├── backend/           # Python package (FastAPI routes, RAG pipeline, Chroma)
├── frontend/          # React + Vite UI
├── scripts/           # CLI helpers, smoke tests
├── main.py            # FastAPI entry
├── Dockerfile         # Production API image
├── docker-compose.yml # Local dev: API + Redis
├── render.yaml        # Render Blueprint (backend)
└── requirements.txt
```

## Local development

```bash
cp .env.example .env
# Set GEMINI_API_KEY in .env

# Backend (with Redis via Docker)
docker compose up --build

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

The UI talks to `http://localhost:8000` by default. To point at another API, set `VITE_API_URL` in `frontend/.env` (see `frontend/.env.example`).

## Production: Vercel (frontend) + Render (backend)

### 1. Deploy the API on Render

1. Push this repo to GitHub/GitLab.
2. In [Render](https://render.com), **New → Blueprint** and connect the repo, or **New → Web Service** with **Docker**.
3. Use the repo root; [`Dockerfile`](Dockerfile) builds the API. Port **8000**.
4. Add a **persistent disk** mounted at **`/app/chroma_db`** (1 GB is enough to start).
5. Create a **Redis** instance (Render Redis or external). Set **`REDIS_URL`** on the web service to the **Internal Redis URL** (or connection string your provider gives you).
6. Set environment variables:

| Variable | Example |
|----------|---------|
| `GEMINI_API_KEY` | Your Google AI Studio key |
| `CHROMA_PERSIST_DIR` | `/app/chroma_db` |
| `REDIS_URL` | From Redis service |
| `LOG_LEVEL` | `INFO` |
| `CORS_ORIGINS` | `https://your-app.vercel.app` (comma-separated if multiple) |

7. Deploy and wait until **`/health`** returns 200.

Optional: commit [`render.yaml`](render.yaml) and use **Blueprint** for a one-click skeleton; you still need to add **Redis** in the dashboard and set `REDIS_URL` if not defined in the blueprint.

### 2. Deploy the frontend on Vercel

1. **New Project** → import the same repo.
2. Set **Root Directory** to **`frontend`**.
3. Framework: Vite (auto). Build: `npm run build`, output: **`dist`**.
4. Add environment variable:

   - **`VITE_API_URL`** = `https://<your-render-service>.onrender.com` (no trailing slash)

5. Deploy. Open the Vercel URL; the header should show **API Connected** if CORS and the API URL are correct.

### 3. First-time indexing

Open the live app and use **Sync Docs** once. Ingestion can take several minutes depending on Gemini quotas. Chroma data persists on the Render disk.

### 4. Smoke test

```bash
API_URL=https://your-service.onrender.com ./scripts/smoke_prod.sh
```

Manually verify chat and a few quick actions; check Render logs for errors or repeated `429` responses.

## Operations

- **Rotate API key:** Update `GEMINI_API_KEY` in Render → **Manual Deploy** to restart.
- **Re-ingest:** Use **Sync Docs** in the UI; existing chunk IDs are skipped when possible (see `backend/services/ingest.py`).
- **Clear vector store:** Remove the Chroma volume data only if you intend to re-embed everything (quota-heavy).

## RAG pipeline (overview)

```
User Query → Redis memory → Embed query → Chroma retrieval → Gemini answer → Sources
```

## Key design notes

- Semantic chunking, Gemini embeddings, Chroma cosine search, Gemini chat model for answers.
- Conversation memory: Redis sliding window per `session_id`.
- Incremental ingestion with chunk-level skip when IDs already exist in Chroma.
