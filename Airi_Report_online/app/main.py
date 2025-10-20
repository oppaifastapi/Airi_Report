# app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# --- Routers (있는 것만 import) ---
from app.routers.portfolio import router as portfolio_router
from app.routers.prices import router as prices_router
from app.routers.summary import router as summary_router
from app.routers.prices_table_data import router as prices_data_router  # ← 새 데이터 전용 API

# --- App 생성은 먼저! ---
app = FastAPI(title="AiRi Erobook Server", version="0.1.0")

# (선택) CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# --- 기본 라우트 ---
@app.get("/", response_class=JSONResponse)
def root():
    return {"message": "💕아이리 서버 작동 중이에요!💕"}

# --- 라우터 등록 (App 생성 이후에!) ---
app.include_router(prices_data_router)   # /prices_table-data
app.include_router(portfolio_router)     # /portfolio-editor 등
app.include_router(prices_router)        # /prices_table-html 등
app.include_router(summary_router)       # /daily-summary-html 등

@app.get("/healthz")
def healthz():
    return {"status": "ok"}
