@echo off
chcp 65001 >nul
echo ========================================
echo   Auto All System - Dev Mode
echo ========================================
echo.

cd /d "%~dp0"

echo [1/6] Check Docker...
docker version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker not running
    pause
    exit /b 1
)
echo [OK] Docker is running

echo.
echo [2/6] Starting DB and Redis...
docker-compose up -d db redis
if errorlevel 1 (
    echo [ERROR] Failed to start DB
    pause
    exit /b 1
)
echo [OK] DB and Redis started

echo.
echo [3/6] Waiting for DB...
timeout /t 5 /nobreak >nul
echo [OK] DB ready

echo.
echo [4/6] Prepare backend...
if not exist "backend\logs" mkdir backend\logs
echo [OK] Logs directory ready

echo.
echo [5/6] Starting backend...
docker-compose up -d backend celery celery-beat
if errorlevel 1 (
    echo [ERROR] Failed to start backend
    pause
    exit /b 1
)
echo [OK] Backend started

echo.
echo [5.5/6] Reload backend containers...
docker-compose restart backend celery celery-beat >nul 2>&1
echo [OK] Backend reloaded

REM Stop Docker frontend to avoid port conflict
docker-compose stop frontend >nul 2>&1

echo.
echo [6/6] Starting frontend dev server...

cd frontend

REM Check if node_modules exists
if not exist "node_modules" (
    echo [INFO] Installing dependencies...
    npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed
)

echo.
echo ========================================
echo   Backend services ready!
echo ========================================
echo.
echo Frontend Dev: http://localhost:3000/
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

start http://localhost:3000/
npm run dev
