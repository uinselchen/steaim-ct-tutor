@echo off
setlocal

set "ROOT=%~dp0"
set "PY=%ROOT%app\venv\Scripts\python.exe"

if not exist "%PY%" (
    set "PY=python"
)

echo STEaiM-CT Tutor test run
echo ========================
echo.

"%PY%" -m unittest discover -s "%ROOT%tests" -p "test_*.py" -v
exit /b %ERRORLEVEL%
