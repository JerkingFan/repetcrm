@echo off
cd /d "%~dp0..\backend"
.\.venv\Scripts\python scripts\latex_to_python.py %*
