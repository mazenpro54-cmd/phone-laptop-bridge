@echo off
title Phone-to-Laptop Bridge
cd /d "%~dp0"
echo Starting Phone-to-Laptop Bridge...
venv\Scripts\python.exe run.py
pause
