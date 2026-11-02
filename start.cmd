@echo off
rem PrismQuant A2 political monitoring agent (thin wrapper)
cd /d "%~dp0"
set "PY=C:\Users\Admin\.workbuddy\binaries\python\versions\3.13.12\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" -m app.seed
"%PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8120
pause
