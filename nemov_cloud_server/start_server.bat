@echo off
title Yalda Cloud Backup Server
echo Starting Yalda Cloud Backup Server on http://localhost:8000 ...
if exist "..\venv\Scripts\python.exe" (
    ..\venv\Scripts\python.exe -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
) else (
    python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
)
pause