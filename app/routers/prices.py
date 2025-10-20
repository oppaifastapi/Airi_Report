from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import time, json
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from app.core.auth import require_auth

import yfinance as yf

router = APIRouter()

# ----- 절대경로: 프로젝트 루트/data/holdings.json -----
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "data" / "holdings.json"

def load_tickers_from_holdings() -> List[str]:
    if not DATA_PATH.exists():
        return []
    try:
        raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        pos = raw.get("positions", raw)
        if isinstance(pos, dict):
            return [str(k).upper() for k in pos.keys()]
        if isinstance(pos, list):
            return [str(x).upper() for x in pos]
        return []
    except Exception:
        return []

# -------------------- 10분 캐시 --------------------
_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL = 600

def get_cached(sym: str):
    item = _CACHE.get(sym)
    if item and (time.time() - item["t"] < CACHE_TTL):
        return item["data"]
    return None

def set_cached(sym: str, data: Dict[str, Any]):
    _CACHE[sym] = {"t": time.time(), "data": data}

def fetch_metrics(sym: str) -> Dict[str, Any]:
    cached = get_cached(sym)
    if cached: return cached
    try:
        tk = yf.Ticker(sym)
        hist = tk.history(period="7d", interval="1d", auto_adjust=False)
        closes = hist["Close"].dropna().tolist()
        volume = None
        try:
            volume = int(hist["Volume"].dropna().iloc[-1])
        except Exception:
            volume = None

        close = prev = change_pct = None
        if len(closes) >= 2:
            close, prev = float(closes[-1]), float(closes[-2])
            if prev != 0:
                change_pct = round((close - prev) / prev * 100, 2)

        marketcap = None
        try:
            info = tk.fast_info
            marketcap = float(info.get("market_cap")) if info and info.get("market_cap") else None
        except Exception:
            marketcap = None

        data = {
            "ticker": sym,
            "close": close,
            "prev_close": prev,
            "change_pct": change_pct,
            "marketcap": marketcap,
            "volume": volume,
        }
        set_cached(sym, data)
        return data
    except Exception:
        return {"ticker": sym, "close": None, "prev_close": None, "change_pct": None, "marketcap": None, "volume": None}

def compact_num_krw(x) -> str:
    if x is None: return "-"
    try: v = float(x)
    except: return "-"
    if v >= 1_0000_0000_0000: return f"{round(v/1_0000_0000_0000,2)}조원"
    if v >= 1_0000_0000:       return f"{round(v/1_0000_0000,2)}억원"
    return f"{int(v):,}원"

@router.get("/prices_table-html", response_class=HTMLResponse)
def prices_table_html(
    tickers: Optional[str] = Query(None, description="수동 지정 시: NVDA,GOOG"),
    _: None = Depends(require_auth),
):
    syms = [t.strip().upper() for t in tickers.split(",") if t.strip()] if tickers else load_tickers_from_holdings()
    if not syms:
        return HTMLResponse(f"<html><body><p>holdings.json에 종목이 없습니다.<br><small>path: {DATA_PATH}</small></p></body></html>")

    rows = [fetch_metrics(sym) for sym in syms]
    asof = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    head = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Prices</title>
<style>
body{{font-family:system-ui,Segoe UI,Roboto,Apple SD Gothic Neo,Malgun Gothic,Arial,sans-serif;padding:16px}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #e5e7eb;padding:10px;text-align:right}}
th{{background:#f8fafc;text-align:center}}
td.t{{text-align:left}}
.pos{{color:#0b875b;font-weight:600}}
.neg{{color:#c0392b;font-weight:600}}
.caption{{margin-bottom:10px;font-weight:600}}
.muted{{color:#6b7280}}
</style></head><body>
<div class="caption">📊 Prices (as of {asof}) <span class="muted">10분 캐시</span></div>
<table><thead><tr>
  <th class="t">Ticker</th><th>Close</th><th>Prev</th><th>Δ%</th><th>MarketCap</th><th>Volume</th>
</tr></thead><tbody>
"""
    body = []
    for r in rows:
        chg = r.get("change_pct")
        chg_cls = "" if chg is None else ("pos" if chg >= 0 else "neg")
        chg_str = "-" if chg is None else f"{chg:+.2f}%"
        close = "-" if r.get("close") is None else f"{r['close']:,.2f}"
        prev  = "-" if r.get("prev_close") is None else f"{r['prev_close']:,.2f}"
        mcap  = compact_num_krw(r.get("marketcap"))
        vol   = "-" if r.get("volume") is None else f"{int(r['volume']):,}"
        body.append(
            f"<tr><td class='t'>{r.get('ticker','-')}</td>"
            f"<td>{close}</td><td>{prev}</td>"
            f"<td class='{chg_cls}'>{chg_str}</td>"
            f"<td>{mcap}</td><td>{vol}</td></tr>"
        )

    tail = "</tbody></table></body></html>"
    return HTMLResponse(head + "\n".join(body) + tail)
