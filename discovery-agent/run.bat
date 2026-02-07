@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt -q 2>nul
python run.py %*
exit /b %ERRORLEVEL%
