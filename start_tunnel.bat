@echo off
title Cloudflare Tunnel (Remote Phone Access)
cd /d "%~dp0"
echo Starting Cloudflare Tunnel to your Laptop Bridge...
echo Look for the URL ending with .trycloudflare.com below!
echo.
if exist "C:\Program Files (x86)\cloudflared\cloudflared.exe" (
    "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:8000
) else if exist "C:\Program Files\cloudflared\cloudflared.exe" (
    "C:\Program Files\cloudflared\cloudflared.exe" tunnel --url http://localhost:8000
) else (
    cloudflared tunnel --url http://localhost:8000
)
pause
