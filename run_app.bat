@echo off
setlocal
cd /d "%~dp0"

set "VENV_PYTHON=.venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    py -3 -m venv .venv
    if errorlevel 1 exit /b %errorlevel%
)

"%VENV_PYTHON%" -c "import altair, pandas, sklearn, streamlit" >nul 2>&1
if errorlevel 1 (
    "%VENV_PYTHON%" -m pip install -r requirements.txt
    if errorlevel 1 exit /b %errorlevel%
)

"%VENV_PYTHON%" -m streamlit run frontend\streamlit_app_v2.py
exit /b %errorlevel%
