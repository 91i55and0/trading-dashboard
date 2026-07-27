@echo off
chcp 65001 >nul 2>&1
title Trading Dashboard

echo Starting services...
echo.

REM Start backend
start "Backend" cmd /k "cd /d %~dp0backend && python main.py"

echo Waiting for backend (5s)...
timeout /t 5 /nobreak >nul

REM Start frontend
start "Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo Waiting for frontend (3s)...
timeout /t 3 /nobreak >nul

start http://localhost:5173

echo.
echo Done! http://localhost:5173
echo Close this window after use.
echo.
pause
