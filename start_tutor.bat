@echo off
setlocal enabledelayedexpansion

set "ROOT=%~dp0"
set "APP=%ROOT%app"
set "VENV=%APP%\venv"

set "DIRS=app app\server app\frontend app\frontend\css app\frontend\js app\frontend\assets app\data app\data\curricula app\data\lessonplans app\data\templates app\data\outputs"
for %%D in (%DIRS%) do (
    if not exist "%ROOT%%%D\" (
        mkdir "%ROOT%%%D\"
    )
)

if not exist "%VENV%\Scripts\python.exe" (
    echo Creating local virtual environment...
    python -m venv "%VENV%" 2>nul
    if errorlevel 1 (
        py -3 -m venv "%VENV%" 2>nul
    )
    if not exist "%VENV%\Scripts\python.exe" (
        echo Failed to create local virtual environment.
        echo Please install Python 3 and make it available on PATH.
        pause
        exit /b 1
    )
)

echo Starting local tutor...
call "%VENV%\Scripts\activate.bat"
pushd "%APP%\server"
python app.py
popd
