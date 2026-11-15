@echo off
title Laptop Remote - Bridge & Tunnel
cd /d "%~dp0"

echo ========================================================
echo        STARTING LAPTOP REMOTE BRIDGE & TUNNEL
echo ========================================================
echo.

:: Kill any existing cloudflared or python run instances to avoid port conflicts
taskkill /F /IM cloudflared.exe 2>nul

echo [1/2] Starting Python Bridge Server...
start "1. Bridge Server (Python)" cmd /k "venv\Scripts\python.exe run.py"

echo Waiting 2 seconds for server to start...
timeout /t 2 /nobreak >nul

echo [2/2] Starting Cloudflare Tunnel...
if exist "C:\Program Files (x86)\cloudflared\cloudflared.exe" (
    start "2. Cloudflare Tunnel" cmd /k ""C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://127.0.0.1:8000"
) else (
    start "2. Cloudflare Tunnel" cmd /k "cloudflared tunnel --url http://127.0.0.1:8000"
)

echo.
echo ========================================================
echo BOTH SERVICES ARE NOW RUNNING ON YOUR LAPTOP!
echo.
echo Look at the "2. Cloudflare Tunnel" window:
echo Copy your link (ending in .trycloudflare.com)
echo and paste it into: https://phone-laptop-bridge.vercel.app
echo ========================================================
echo.
pause
