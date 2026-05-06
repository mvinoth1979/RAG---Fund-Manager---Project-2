@echo off
echo =======================================================
echo    Starting Mutual Fund FAQ Assistant (Phases 1-7)
echo =======================================================

echo.
echo [1/2] Booting FastAPI Backend Orchestrator (Phases 1-6)...
start "FastAPI Backend" cmd /k "uvicorn phase_6_response_delivery.api:app --host 127.0.0.1 --port 8000"

echo.
echo [2/2] Booting React UI (Phase 7)...
cd phase_7_frontend
start "React Frontend" cmd /k "npm run dev"

echo.
echo Both systems are now booting up!
echo Backend API will be available at: http://localhost:8000
echo Frontend UI will be available at: http://localhost:5173
echo =======================================================
