@echo off
chcp 65001 >nul
echo ========================================
echo   Auto All System - Dev Mode
echo ========================================
echo.

cd /d "%~dp0"

echo [1/5] Check Docker...
docker version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker not running
    pause
    exit /b 1
)
echo [OK] Docker is running

echo.
echo [2/5] Starting DB and Redis...
docker-compose up -d db redis
if errorlevel 1 (
    echo [ERROR] Failed to start DB
    pause
    exit /b 1
)
echo [OK] DB and Redis started

echo.
echo [3/5] Waiting for DB...
timeout /t 5 /nobreak >nul
echo [OK] DB ready

echo.
echo [4/5] Starting backend...
docker-compose up -d backend celery celery-beat
if errorlevel 1 (
    echo [ERROR] Failed to start backend
    pause
    exit /b 1
)
echo [OK] Backend started

echo.
echo [5/5] Starting frontend dev server...
echo.
echo ========================================
echo   Backend services ready!
echo ========================================
echo.
echo Frontend Dev: http://localhost:5173/
echo Backend API:  http://localhost:8000/api/
echo API Docs:     http://localhost:8000/api/docs/
echo.
echo Tips:
echo   - Frontend auto hot-reload on save
echo   - Backend restart: docker-compose restart backend
echo   - Stop all: docker-compose down
echo.
echo ----------------------------------------
echo   Starting frontend dev server...
echo ----------------------------------------
echo.

cd frontend
start http://localhost:5173/
npm run dev
