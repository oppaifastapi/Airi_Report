from typing import Dict, Any
import yfinance as yf

def get_usdkrw() -> float:
    try:
        fx = yf.Ticker("KRW=X").history(period="5d", interval="1d")
        return float(fx["Close"].dropna().iloc[-1])
    except Exception:
        return 1350.0

def fetch_last_change_pct(sym: str) -> Dict[str, Any]:
    try:
        hist = yf.Ticker(sym).history(period="7d", interval="1d", auto_adjust=False)
        closes = hist["Close"].dropna().tolist()
        if len(closes) >= 2:
            _last, _prev = float(closes[-1]), float(closes[-2])
            change_pct = round(((_last - _prev) / _prev) * 100, 4) if _prev != 0 else None
            return {"ticker": sym, "close": round(_last,2), "prev_close": round(_prev,2), "change_pct": change_pct}
        elif len(closes) == 1:
            return {"ticker": sym, "close": round(float(closes[-1]),2), "prev_close": None, "change_pct": None}
        return {"ticker": sym, "error": "종가 데이터 없음(휴장/상장 이슈 가능)"}
    except Exception as e:
        return {"ticker": sym, "error": str(e)}

def build_price_row(sym: str, usdkrw: float) -> Dict[str, Any]:
    base = fetch_last_change_pct(sym)
    name = sym
    try:
        tkr = yf.Ticker(sym)
        fi = tkr.fast_info
        if isinstance(fi, dict) and fi.get("shortName"):
            name = fi["shortName"]
        else:
            info = tkr.info
            if isinstance(info, dict) and info.get("shortName"):
                name = info["shortName"]
    except Exception:
        pass
    volume = None
    try:
        h = yf.Ticker(sym).history(period="7d", interval="1d", auto_adjust=False)
        volume = int(h["Volume"].dropna().iloc[-1])
    except Exception:
        volume = None
    last_usd = base.get("close")
    prev_usd = base.get("prev_close")
    last_krw = round(last_usd * usdkrw) if last_usd is not None else None
    prev_krw = round(prev_usd * usdkrw) if prev_usd is not None else None
    turnover_krw = round(last_usd * volume * usdkrw) if (last_usd is not None and volume is not None) else None
    return {
        "name": name, "ticker": sym,
        "current_price_krw": last_krw, "current_price_usd": last_usd,
        "change_pct": base.get("change_pct"),
        "turnover_krw": turnover_krw,
        "close_krw": prev_krw, "close_usd": prev_usd,
        "volume": volume, "raw": base
    }

def format_krw_compact(x) -> str:
    if x is None: return "-"
    try:
        v = float(x)
    except Exception:
        return "-"
    if v >= 1_0000_0000_0000:
        return f"{round(v/1_0000_0000_0000,2)}조원"
    if v >= 1_0000_0000:
        return f"{round(v/1_0000_0000,2)}억원"
    return f"{int(v):,}원"
