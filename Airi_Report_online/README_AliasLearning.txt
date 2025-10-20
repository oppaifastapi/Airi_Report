AiRi Portfolio Editor — Alias Learning Pack
===========================================

기능
----
- 티커로 정상 등록 시 상단에 "한글 별칭 저장" 배너 노출
- 입력한 한글 별칭(alias)을 aliases.json에 저장(ko → ticker)
- 이후 보조검색/자동완성에서 한글로 바로 인식
- 한글 검색 파이프라인: FDR(KRX) → NAVER → 별칭 → Yahoo

설치
----
1) 의존성 설치
   pip install fastapi uvicorn yfinance requests FinanceDataReader

2) 파일 배치
   Airi_Report/
     app/
       routers/
         portfolio.py          ← 이 파일로 교체
     data/
       aliases.json            ← 없으면 자동 기본값 사용
       holdings.json           ← 없으면 자동 생성

실행
----
uvicorn app.main:app --reload --port 8000

엔드포인트
----------
- /portfolio-editor           : 편집 페이지
- /portfolio-editor/find      : 이름 보조 검색
- /portfolio-editor/alias-add : 한글 별칭 저장(POST)
- /api/search                 : 자동완성 API
- /portfolio-json             : holdings.json 확인
