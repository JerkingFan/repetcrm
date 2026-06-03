@echo off
cd /d "%~dp0..\backend"
echo Downloading Qwen 0.5B from Hugging Face (~1 GB)...
.\.venv\Scripts\python scripts\download_local_model.py fast
echo.
echo Restart backend: scripts\start-backend.cmd
pause
