@echo off
title AiRi FastAPI Server
cd /d %~dp0

echo ================================
echo   🚀 AiRi FastAPI Server 시작 중
echo ================================
echo.

REM 가상환경을 쓰신다면 여기 활성화
REM call venv\Scripts\activate

uvicorn app.main:app --reload --port 8000

pause
