# AiRi Report — Cleaned Structure (0.1v → 0.1v-clean)

## What I changed
- Added **app/models/schemas.py** (Pydantic models for typed responses)
- Added **app/core/logging.py** and enabled centralized logging in `app/main.py`
- Added **CORS middleware** and a simple global error handler
- Enforced **Bearer auth** dependency on all router endpoints
- Left routing and service logic intact to avoid breaking changes

## How to run
```bash
uvicorn app.main:app --reload --port 8000
```

## Next steps (optional)
- Split HTML-building utilities into `app/views/html.py`
- Add unit tests under `tests/`
- Replace yfinance calls with your internal API when available