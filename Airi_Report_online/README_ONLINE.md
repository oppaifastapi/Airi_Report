# Online Deployment Guide (FastAPI)

This pack lets you move from local to **online** quickly.

## Option A — Render.com (no Docker needed)
1) Push your project to GitHub.
2) Add *render.yaml* to the repo root.
3) On Render, **New > Blueprint** and point to your repo. It will read `render.yaml`.
4) Set `OPPAI_API_TOKEN` in Render **Environment Variables** (optional).
5) Deploy. Health check is `/healthz` (ensure that endpoint exists).

Start command (from `render.yaml`):
```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Option B — Docker (any cloud / your VM)
```
docker build -t airi-report .
docker run -p 8000:8000 --env-file .env airi-report
```
Go to: http://localhost:8000

## Option C — Railway/Heroku
- Include the provided **Procfile** in repo root.
- Set `PORT` env var automatically provided by the platform.
- Start command is the same as above.

## Browser IDE (Online Editing)
- **GitHub Codespaces**: Open your repo in a codespace and run `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- **Replit**: Import your GitHub repo; set Run command to the same `uvicorn` line.
- Commit/push to GitHub; deployment is automated if linked (Render auto-deploy on push).

## CORS (if your web UI is separate)
Add to `app/main.py` once (safe for prod):
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
(Restrict `allow_origins` in production if needed.)

## Health Check
Make sure your app defines:
```python
@app.get("/healthz")
def healthz():
    return {"status": "ok"}
```