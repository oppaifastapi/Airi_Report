from fastapi import APIRouter, Depends, Query, Header
from fastapi.responses import PlainTextResponse, HTMLResponse
from typing import Optional, List
from datetime import datetime, timezone
from markdown import markdown
from app.core.auth import require_auth
from app.core.config import DEFAULT_TICKERS
from app.services.market import fetch_last_change_pct

router = APIRouter()

@router.get("/daily-summary-html", response_class=HTMLResponse)
def daily_summary_html(tickers: Optional[str] = Query(None), authorization: str | None = Header(None), _=Depends(require_auth)):
    require_auth(authorization)
    syms = [t.strip().upper() for t in tickers.split(",") if t.strip()] if tickers else DEFAULT_TICKERS[:]
    rows = [fetch_last_change_pct(sym) for sym in syms]
    asof = datetime.now(timezone.utc).isoformat()
    md = [f"### 📊 Daily Summary (UTC: {asof})"]
    for r in rows:
        if "error" in r: md.append(f"- {r['ticker']}: 오류 — {r['error']}")
        else:
            pct, last, prev = r.get("change_pct"), r.get("close"), r.get("prev_close")
            if pct is None: md.append(f"- {r['ticker']}: 데이터 부족")
            else:
                sign = "+" if pct >= 0 else ""
                md.append(f"- {r['ticker']}: {sign}{pct}% (어제 {prev} → 오늘 {last})")
    html = markdown("\n".join(md))
    return HTMLResponse(f"<html><body>{html}</body></html>")
