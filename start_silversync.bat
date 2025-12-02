@echo off
title SilverSync Launcher
echo ==========================================
echo     SilverSync - Full System Launcher
echo ==========================================

:: Step 1 - Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

:: Step 2 - Start backend
echo Starting SilverSync Backend...
start "SilverSync Backend" cmd /k "uvicorn backend.main:app --reload"

:: Step 3 - Start Real-Time Ingestion Service
echo Starting RealTimeIngestion Service...
start "SilverSync Ingestion" cmd /k "call .\venv\Scripts\activate && python backend\services\RealTimeIngestion.py"

:: Wait a few seconds for backend to initialize
timeout /t 5 >nul

:: Step 4 - Start frontend
echo Starting SilverSync Frontend...
start "SilverSync Frontend" cmd /k "cd frontend\silversync_dashboard && npm run dev"

echo ==========================================
echo  SilverSync Backend and Frontend launched!
echo ==========================================
pause
