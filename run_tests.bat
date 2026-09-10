@echo off
setlocal

set "ROOT=%~dp0"
set "PY=%ROOT%app\venv\Scripts\python.exe"
set "TEST_RUNNER=%ROOT%tests\run_tests.py"

if not exist "%PY%" (
    set "PY=python"
)

"%PY%" "%TEST_RUNNER%"
exit /b %ERRORLEVEL%
