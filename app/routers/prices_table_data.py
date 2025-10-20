from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
import json, time
from pathlib import Path
from typing import List, Dict, Any, Optional
import yfinance as yf
from app.core.auth import require_auth

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "data" / "holdings.json"

CACHE_TTL = 600
_CACHE: Dict[str, Dict[str, Any]] = {}

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

def get_cached(sym: str):
    item = _CACHE.get(sym)
    if item and (time.time() - item["t"] < CACHE_TTL):
        return item["data"]
    return None

def set_cached(sym: str, data: Dict[str, Any]):
    _CACHE[sym] = {"t": time.time(), "data": data}

def fetch_metrics(sym: str) -> Dict[str, Any]:
    cached = get_cached(sym)
    if cached:
        return cached
    try:
        tk = yf.Ticker(sym)
        hist = tk.history(period="7d", interval="1d", auto_adjust=False)
        closes = hist["Close"].dropna().tolist()
        volume = int(hist["Volume"].dropna().iloc[-1]) if not hist["Volume"].dropna().empty else None
        close = prev = change_pct = None
        if len(closes) >= 2:
            close, prev = float(closes[-1]), float(closes[-2])
            if prev != 0:
                change_pct = round((close - prev) / prev * 100, 2)
        info = getattr(tk, "fast_info", {}) or {}
        marketcap = float(info.get("market_cap")) if info and info.get("market_cap") else None
        data = {"ticker": sym, "close": close, "prev_close": prev, "change_pct": change_pct,
                "marketcap": marketcap, "volume": volume}
        set_cached(sym, data)
        return data
    except Exception:
        return {"ticker": sym}

@router.get("/prices_table-data", response_class=JSONResponse)
def prices_table_data(tickers: Optional[str] = Query(None), _: None = Depends(require_auth)):
    syms = [t.strip().upper() for t in tickers.split(",") if t.strip()] if tickers else load_tickers_from_holdings()
    rows = [fetch_metrics(sym) for sym in syms]
    asof_utc = datetime.now(timezone.utc).isoformat()
    return {"asof_utc": asof_utc, "tickers": syms, "rows": rows, "cache_ttl_sec": CACHE_TTL}
