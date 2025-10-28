@echo off
echo Starting Visual Trade Copilot Server...
echo Server will be available at: http://127.0.0.1:8765
echo API docs will be available at: http://127.0.0.1:8765/docs
echo Press Ctrl+C to stop the server
echo.

cd /d "%~dp0"
venv\bin\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8765 --reload
