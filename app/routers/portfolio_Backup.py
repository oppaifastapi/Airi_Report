from fastapi import APIRouter, Form, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.core.auth import require_auth
from pathlib import Path
from urllib.parse import quote_plus
import json, re, requests, datetime
import yfinance as yf
import FinanceDataReader as fdr

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_PATH = BASE_DIR / "data" / "holdings.json"
ALIAS_PATH = BASE_DIR / "data" / "aliases.json"
_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AiRi/1.0"}

# -------------------- 파일 유틸 --------------------
def _ensure_file():
    if not DATA_PATH.exists():
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        seed = {"positions": {}, "meta": {"base_currency": "KRW"}}
        DATA_PATH.write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding="utf-8")

def load_holdings():
    _ensure_file()
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))

def save_holdings(data):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# -------------------- 숫자 파싱 --------------------
_NUM = re.compile(r"[,\s]")
def to_float(s, default=0.0):
    if s is None: return default
    if isinstance(s, (int, float)): return float(s)
    s = _NUM.sub("", str(s))
    try: return float(s)
    except: return default

# -------------------- 별칭 관리 --------------------
def load_aliases() -> dict:
    try:
        if ALIAS_PATH.exists():
            return json.loads(ALIAS_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {
        "엔비디아": "NVDA", "구글": "GOOGL", "알파벳": "GOOGL",
        "테슬라": "TSLA", "마이크로소프트": "MSFT", "마소": "MSFT",
        "애플": "AAPL", "아마존": "AMZN", "메타": "META", "넷플릭스": "NFLX"
    }

def save_aliases(d: dict):
    ALIAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ALIAS_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

def is_hangul(s: str) -> bool:
    return any('\uac00' <= ch <= '\ud7a3' for ch in s)

# -------------------- 검색 유틸 --------------------
def yahoo_symbol_search(query: str, count: int = 8):
    url = "https://query2.finance.yahoo.com/v1/finance/search"
    try:
        r = requests.get(url, params={"q": query, "quotesCount": count, "newsCount": 0}, headers=_UA, timeout=6)
        r.raise_for_status()
        data = r.json()
        return [
            {
                "ticker": q.get("symbol"),
                "longname": q.get("longname") or q.get("shortname") or "",
                "exch": q.get("exchDisp") or q.get("exchange") or "",
                "source": "YAHOO",
            }
            for q in data.get("quotes", [])
        ]
    except Exception:
        return []

def yahoo_quote_name(ticker: str) -> str | None:
    t = (ticker or "").strip().upper()
    if not t: return None
    try:
        r = requests.get("https://query1.finance.yahoo.com/v7/finance/quote",
                         params={"symbols": t}, headers=_UA, timeout=6)
        r.raise_for_status()
        res = r.json()
        q = res.get("quoteResponse", {}).get("result", [])
        if q:
            return q[0].get("longName") or q[0].get("shortName") or None
    except Exception:
        pass
    try:
        tk = yf.Ticker(t)
        info = getattr(tk, "info", {}) or {}
        return info.get("longName") or info.get("shortName") or None
    except Exception:
        return None

def alias_candidate(name_ko: str):
    al = load_aliases()
    t = al.get(name_ko.strip()) or al.get(name_ko.strip().replace(" ",""))
    if not t:
        return None
    nm = yahoo_quote_name(t)
    if not nm:
        return None
    return {"ticker": t, "longname": nm, "exch": "", "source": "ALIAS"}

def krx_candidates_by_name(name_ko: str):
    try:
        df = fdr.StockListing('KRX')
        key = name_ko.strip().lower().replace(" ", "")
        mask = df["Name"].map(lambda x: str(x).strip().lower().replace(" ","")).str.contains(key, na=False)
        sub = df[mask].copy()
        out = []
        for _, row in sub.iterrows():
            code = str(row["Symbol"]).zfill(6)
            market = str(row["Market"])
            suffix = ".KS" if "KOSPI" in market.upper() else ".KQ"
            out.append({
                "ticker": f"{code}{suffix}",
                "longname": row["Name"],
                "exch": market,
                "source": "FDR"
            })
        return out
    except Exception:
        return []

def resolve_name_candidates(name: str):
    name = (name or "").strip()
    cands = []
    if not name:
        return cands
    if is_hangul(name):
        cands += krx_candidates_by_name(name)
    a = alias_candidate(name)
    if a: cands.append(a)
    y = yahoo_symbol_search(name, count=10) or []
    cands += y
    uniq = {}
    for c in cands:
        t = (c.get("ticker") or "").upper()
        if t and t not in uniq:
            uniq[t] = c
    return list(uniq.values())

# -------------------- 페이지 렌더 --------------------
def last_modified_human():
    try:
        ts = DATA_PATH.stat().st_mtime
        dt = datetime.datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "-"

def _render_editor(request: Request):
    data = load_holdings()
    positions = data.get("positions", {})
    toast = request.query_params.get("toast")
    error = request.query_params.get("error")

    style = """
    <style>
      body{font-family:system-ui,'Apple SD Gothic Neo';background:#f9fafb;margin:0;padding:32px;color:#111827}
      .container{max-width:1100px;margin:0 auto}
      .card{background:#fff;border-radius:12px;box-shadow:0 2px 6px rgba(0,0,0,.05);padding:20px;margin-bottom:20px}
      th,td{border-bottom:1px solid #e5e7eb;padding:10px;text-align:center}
      th{background:#f3f4f6;position:sticky;top:0}
      td input{width:90%;padding:6px;border:1px solid #d1d5db;border-radius:6px;text-align:right}
      .btn{padding:6px 12px;border-radius:6px;border:none;cursor:pointer;font-weight:600}
      .btn.primary{background:#3b82f6;color:#fff}
      .btn.danger{background:#ef4444;color:#fff}
      .btn.neutral{background:#e5e7eb;color:#111}
      .note{font-size:14px;color:#6b7280;margin-top:6px}
      .alert{padding:12px;border-radius:8px;margin:10px 0}
      .alert.err{background:#fee2e2;color:#991b1b;border:1px solid #fecaca}
      .alert.ok{background:#dcfce7;color:#065f46;border:1px solid #bbf7d0}
    </style>
    """

    head = f"<div class='container'><h2>📒 Portfolio Editor — 티커 우선 <span style='font-size:14px;color:#6b7280'>Last saved {last_modified_human()}</span></h2>"

    msg = ""
    if error: msg += f"<div class='alert err'>⚠️ {error}</div>"
    if toast: msg += f"<div class='alert ok'>✅ {toast}</div>"

    rows = ""
    for sym, info in positions.items():
        name, qty, avg = info.get("name",""), info.get("qty",""), info.get("avg_price_krw","")
        rows += f"""
        <tr>
          <td><input type='text' value='{name}' readonly></td>
          <td><b>{sym}</b></td>
          <td><form method='post' action='/portfolio-editor/save'>
          <input type='hidden' name='ticker' value='{sym}'>
          <input name='qty' type='number' step='0.0001' value='{qty}'></td>
          <td><input name='avg_price_krw' type='number' step='0.01' value='{avg}'></td>
          <td>
            <button class='btn primary' type='submit'>💾 저장</button></form>
            <a class='btn danger' href='/portfolio-editor/delete?ticker={quote_plus(sym)}' onclick='return confirm("삭제할까요? {sym}")'>🗑 삭제</a>
          </td>
        </tr>"""

    table = f"<div class='card'><table><thead><tr><th>종목명</th><th>티커</th><th>보유수량</th><th>평단(₩)</th><th>작업</th></tr></thead><tbody>{rows}</tbody></table></div>"

    add_form = """
    <div class='card'>
      <h3>➕ 새 종목 추가</h3>
      <form method='post' action='/portfolio-editor/add' style='display:flex;gap:10px;flex-wrap:wrap'>
        <input name='ticker' placeholder='티커 (예: NVDA, GOOGL, 005930.KS)' style='flex:1;min-width:220px'>
        <input name='qty' type='number' step='0.0001' placeholder='수량' style='width:100px'>
        <input name='avg_price_krw' type='number' step='0.01' placeholder='평단(₩)' style='width:140px'>
        <button class='btn neutral' type='submit'>추가</button>
      </form>
      <div class='note'>
        이름은 자동으로 채워집니다. 한글 검색은
        <a id='link-find' href='#' style='color:#2563eb'>여기</a>를 이용하세요.
      </div>
    </div>
    """

    find_box = """
    <div class='card' id='findBox'>
      <h3>🔎 이름으로 찾기 (보조 검색)</h3>
      <form method='get' action='/portfolio-editor/find' style='display:flex;gap:10px;flex-wrap:wrap'>
        <input name='name' placeholder='예: 엔비디아, 삼성전자, 테슬라, Apple' style='flex:1;min-width:260px'>
        <button class='btn primary' type='submit'>후보 검색</button>
      </form>
      <div class='note'>한글명 검색은 FDR·별칭·야후 세 단계를 거칩니다.</div>
    </div>
    <script>
    document.addEventListener('click', e=>{
      if(e.target && e.target.id==='link-find'){
        e.preventDefault();
        const box=document.getElementById('findBox');
        if(box){
          box.scrollIntoView({behavior:'smooth'});
          box.style.boxShadow='0 0 0 3px rgba(96,165,250,.8)';
          setTimeout(()=>{box.style.boxShadow='';},1200);
        }
      }
    });
    </script>
    """

    html = f"<html><head><meta charset='utf-8'><title>Portfolio Editor</title>{style}</head><body>{head}{msg}{table}{add_form}{find_box}</div></body></html>"
    return HTMLResponse(html)

# -------------------- 라우트들 --------------------
@router.get("/portfolio-editor", response_class=HTMLResponse)
def portfolio_editor(request: Request, _: None = Depends(require_auth)):
    return _render_editor(request)

@router.post("/portfolio-editor/add")
def add_position(ticker: str = Form(...), qty: str = Form("0"), avg_price_krw: str = Form("0"), _: None = Depends(require_auth)):
    sym = (ticker or "").strip().upper()
    if not sym:
        return RedirectResponse("/portfolio-editor?error=" + quote_plus("티커를 입력해 주세요."), status_code=302)
    name = yahoo_quote_name(sym)
    if not name:
        return RedirectResponse("/portfolio-editor?error=" + quote_plus(f"'{sym}' 은(는) 야후 파이낸스에서 찾을 수 없어요."), status_code=302)
    data = load_holdings()
    pos = data.get("positions", {})
    pos[sym] = {"name": name, "qty": to_float(qty), "avg_price_krw": to_float(avg_price_krw)}
    data["positions"] = pos
    save_holdings(data)
    return RedirectResponse("/portfolio-editor?toast=" + quote_plus(f"추가 완료: {sym}"), status_code=302)

@router.post("/portfolio-editor/save")
def save_position(ticker: str = Form(...), qty: str = Form("0"), avg_price_krw: str = Form("0"), _: None = Depends(require_auth)):
    sym = (ticker or "").strip().upper()
    data = load_holdings()
    if sym in data.get("positions", {}):
        data["positions"][sym]["qty"] = to_float(qty)
        data["positions"][sym]["avg_price_krw"] = to_float(avg_price_krw)
        save_holdings(data)
        return RedirectResponse("/portfolio-editor?toast=" + quote_plus(f"저장 완료: {sym}"), status_code=302)
    return RedirectResponse("/portfolio-editor?error=" + quote_plus("대상 티커를 찾을 수 없어요."), status_code=302)

@router.get("/portfolio-editor/delete")
def delete_position(ticker: str = Query(...), _: None = Depends(require_auth)):
    sym = (ticker or "").strip().upper()
    data = load_holdings()
    if sym in data.get("positions", {}):
        del data["positions"][sym]
        save_holdings(data)
        return RedirectResponse("/portfolio-editor?toast=" + quote_plus(f"삭제 완료: {sym}"), status_code=302)
    return RedirectResponse("/portfolio-editor?error=" + quote_plus("대상 티커를 찾을 수 없어요."), status_code=302)

@router.get("/portfolio-editor/find", response_class=HTMLResponse)
def find_by_name(name: str = Query(""), _: None = Depends(require_auth)):
    q = (name or "").strip()
    if not q:
        return RedirectResponse("/portfolio-editor?error=" + quote_plus("검색할 이름을 입력해 주세요."), status_code=302)
    cands = resolve_name_candidates(q)
    if not cands:
        return RedirectResponse("/portfolio-editor?error=" + quote_plus(f"‘{q}’ 후보를 찾지 못했어요."), status_code=302)
    html = ["<html><head><meta charset='utf-8'><title>후보 선택</title></head><body><div class='container'><h3>‘{}’ 후보 선택</h3><ul>".format(q)]
    for c in cands:
        html.append(
            f"<li style='margin:8px 0'><form method='post' action='/portfolio-editor/add' style='display:inline'>"
            f"<input type='hidden' name='ticker' value='{c['ticker']}'>"
            f"<button class='btn primary' type='submit'>등록</button></form> "
            f"<b>{c['ticker']}</b> - {c['longname']} <span class='note'>({c['exch']})</span> <span style='color:#9ca3af'>[{c['source']}]</span></li>"
        )
    html.append("</ul><a class='btn neutral' href='/portfolio-editor'>↩ 돌아가기</a></div></body></html>")
    return HTMLResponse("".join(html))

@router.get("/portfolio-json", response_class=JSONResponse)
def portfolio_json(_: None = Depends(require_auth)):
    return JSONResponse({"path": str(DATA_PATH), "data": load_holdings()})
