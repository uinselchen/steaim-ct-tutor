@echo off
chcp 65001 >nul 2>&1
setlocal EnableExtensions DisableDelayedExpansion
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

if defined STEAIM_TUTOR_BATCH_ACTIVE (
    echo ERROR: start_tutor.bat was called recursively.
    echo This usually means the launcher file is outdated or was started through another batch wrapper.
    echo Please download the latest project version and run start_tutor.bat directly.
    exit /b 1
)
set "STEAIM_TUTOR_BATCH_ACTIVE=1"

set "ROOT=%~dp0"
set "APP=%ROOT%app"
set "SERVER=%APP%\server"
set "FRONTEND=%APP%\frontend"
set "DATA=%APP%\data"
set "VENV=%APP%\venv"
set "PY=%VENV%\Scripts\python.exe"
set "BUNDLED_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
set "PYTHON_INSTALLER_URL=https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
set "PYTHON_INSTALLER=%TEMP%\steaimct-python-3.12.10-amd64.exe"
set "LOGDIR=%DATA%\outputs"
set "LOGFILE=%LOGDIR%\server.log"
set "ANALYSIS_LOG=%LOGDIR%\analysis-log.txt"
set "PROMPT_LOG=%LOGDIR%\mistral-prompt-log.txt"
set "REQUIREMENTS=%SERVER%\requirements.txt"
set "KEY_FILE=%SERVER%\mistral_api_key.txt"
set "ENV_FILE=%SERVER%\.env"
set "ENV_EXAMPLE=%SERVER%\.env.example"
set "CONFIG_FILE=%DATA%\config.json"
set "TUTOR_URL=http://localhost:8000"
set "WARNINGS=0"
set "STARTUP_DIAGNOSTIC=%TEMP%\steaimct-tutor-startup.log"

> "%STARTUP_DIAGNOSTIC%" echo STEaiM-CT Tutor startup diagnostic
>> "%STARTUP_DIAGNOSTIC%" echo Started: %DATE% %TIME%
>> "%STARTUP_DIAGNOSTIC%" echo Launcher: %~f0
>> "%STARTUP_DIAGNOSTIC%" echo Arguments: %*

title STEaiM-CT Tutor
echo(
echo STEaiM-CT Tutor startup check
echo =============================
echo(
echo Startup diagnostic: "%STARTUP_DIAGNOSTIC%"
echo(

call :ensure_dir "%APP%" || goto fail
call :ensure_dir "%SERVER%" || goto fail
call :ensure_dir "%FRONTEND%" || goto fail
call :ensure_dir "%FRONTEND%\css" || goto fail
call :ensure_dir "%FRONTEND%\js" || goto fail
call :ensure_dir "%FRONTEND%\assets" || goto fail
call :ensure_dir "%DATA%" || goto fail
call :ensure_dir "%DATA%\curricula" || goto fail
call :ensure_dir "%DATA%\amendments" || goto fail
call :ensure_dir "%DATA%\lessonplans" || goto fail
call :ensure_dir "%DATA%\lessonplans\uploads" || goto fail
call :ensure_dir "%DATA%\templates" || goto fail
call :ensure_dir "%LOGDIR%" || goto fail
call :ensure_dir "%LOGDIR%\exports" || goto fail
call :ensure_dir "%LOGDIR%\step3-sessions" || goto fail

call :ensure_file "%ANALYSIS_LOG%" || goto fail
call :ensure_file "%PROMPT_LOG%" || goto fail
call :ensure_file "%LOGFILE%" || goto fail

if not exist "%CONFIG_FILE%" (
    echo Creating default config...
    > "%CONFIG_FILE%" echo {
    >> "%CONFIG_FILE%" echo   "countries": ["Slovakia", "Germany", "Austria", "Spain", "Czech Republic", "Poland", "Portugal", "Italy"],
    >> "%CONFIG_FILE%" echo   "subjects": ["Mathematics", "Informatics / CS", "Biology", "Physics", "Chemistry", "Arts"]
    >> "%CONFIG_FILE%" echo }
)

if not exist "%ENV_EXAMPLE%" (
    echo Creating .env.example...
    > "%ENV_EXAMPLE%" echo MISTRAL_API_URL=https://api.mistral.ai/v1/chat/completions
    >> "%ENV_EXAMPLE%" echo MISTRAL_MODEL=mistral-small-latest
    >> "%ENV_EXAMPLE%" echo(
    >> "%ENV_EXAMPLE%" echo # Optional email settings
    >> "%ENV_EXAMPLE%" echo SMTP_HOST=
    >> "%ENV_EXAMPLE%" echo SMTP_PORT=587
    >> "%ENV_EXAMPLE%" echo SMTP_USERNAME=
    >> "%ENV_EXAMPLE%" echo SMTP_PASSWORD=
    >> "%ENV_EXAMPLE%" echo SMTP_USE_TLS=true
    >> "%ENV_EXAMPLE%" echo SMTP_USE_SSL=false
    >> "%ENV_EXAMPLE%" echo MAIL_FROM_ADDRESS=
    >> "%ENV_EXAMPLE%" echo MAIL_TO_ADDRESS=
)

if not exist "%ENV_FILE%" (
    echo Creating .env from .env.example...
    copy "%ENV_EXAMPLE%" "%ENV_FILE%" >nul
)

call :ensure_file "%KEY_FILE%" || goto fail
for %%A in ("%KEY_FILE%") do if %%~zA==0 (
    set /a WARNINGS+=1
    echo WARNING: No Mistral API key configured yet.
    echo Enter it in Admin settings after the tutor opens.
)

call :require_file "%SERVER%\app.py" "server"
call :require_file "%FRONTEND%\start.html" "start screen"
call :require_file "%FRONTEND%\lesson-info.html" "step 1 screen"
call :require_file "%FRONTEND%\first-analysis-and-suggestions.html" "step 2 screen"
call :require_file "%FRONTEND%\refining-and-improving.html" "step 3 screen"
call :require_file "%FRONTEND%\download-result.html" "step 4 screen"
call :require_file "%FRONTEND%\css\style.css" "stylesheet"
call :require_file "%FRONTEND%\js\app.js" "start screen script"
call :require_file "%FRONTEND%\js\lesson-info.js" "step 1 script"
call :require_file "%FRONTEND%\assets\STEaiM_Logo_lowres.png" "STEaiM logo"
call :require_file "%FRONTEND%\assets\eu_funded_en.jpg" "EU co-funded logo"
call :require_file "%SERVER%\prompts\analysis_system_prompt.txt" "analysis prompt"
call :require_file "%SERVER%\prompts\refinement_system_prompt.txt" "refinement prompt"
call :require_file "%SERVER%\prompts\mistral_test_system_prompt.txt" "Mistral test prompt"

if not exist "%REQUIREMENTS%" (
    echo Creating Python requirements file...
    > "%REQUIREMENTS%" echo python-docx^>=1.1.2
    >> "%REQUIREMENTS%" echo pypdf^>=4.2.0
    >> "%REQUIREMENTS%" echo reportlab^>=4.2.0
)

call :ensure_python || goto fail

echo Checking Python packages...
call :probe_python_packages
if errorlevel 1 (
    echo Installing required Python packages...
    "%PY%" -m pip install --upgrade pip
    if errorlevel 1 goto package_fail
    "%PY%" -m pip install -r "%REQUIREMENTS%"
    if errorlevel 1 goto package_fail
)

if not exist "%DATA%\curricula\austria_lehrplan_volksschule_ris_2025_anlage_a.txt" (
    set /a WARNINGS+=1
    echo WARNING: Austrian curriculum text was not found. Curriculum matching may be limited.
)

echo(
if "%WARNINGS%"=="0" (
    echo Startup check passed.
) else (
    echo Startup check finished with %WARNINGS% warnings.
)

if /I "%~1"=="--check" (
    echo Check mode finished. Server was not started.
    exit /b 0
)

if /I "%~1"=="--test" (
    echo Test mode. Server was not started.
    echo(
    call "%ROOT%run_tests.bat"
    exit /b %ERRORLEVEL%
)

echo(
echo Starting local tutor...
echo Server log: "%LOGFILE%"
echo Prompt log: "%PROMPT_LOG%"
echo(

pushd "%SERVER%"
echo ==== %DATE% %TIME% ==== > "%LOGFILE%"
start "" "%TUTOR_URL%"
"%PY%" -X utf8 app.py >> "%LOGFILE%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"
popd

if not "%EXIT_CODE%"=="0" (
    echo(
    echo The tutor stopped with error code %EXIT_CODE%.
    echo See "%LOGFILE%" for the full server log.
    pause
    exit /b %EXIT_CODE%
)

exit /b 0

:ensure_dir
if not exist "%~1\" (
    echo Creating folder: %~1
    mkdir "%~1" >nul 2>nul
    if errorlevel 1 (
        echo Could not create folder: %~1
        exit /b 1
    )
)
exit /b 0

:ensure_file
if not exist "%~1" (
    echo Creating file: %~1
    type nul > "%~1"
    if errorlevel 1 (
        echo Could not create file: %~1
        exit /b 1
    )
)
exit /b 0

:require_file
if not exist "%~1" (
    set /a WARNINGS+=1
    echo WARNING: Missing %~2: "%~1"
)
exit /b 0

:ensure_python
if not exist "%PY%" goto create_python_env

call :probe_python
if not errorlevel 1 exit /b 0

echo Local Python environment is broken. Recreating it...
rmdir /s /q "%VENV%" >nul 2>nul
if exist "%PY%" (
    echo Could not remove the broken Python environment.
    echo Please close all tutor/server windows and run start_tutor.bat again.
    exit /b 1
)

:create_python_env
call :create_venv
if errorlevel 1 exit /b 1

if not exist "%PY%" (
    echo Could not create the local Python environment.
    echo Please install Python 3.11 or newer and run this file again.
    exit /b 1
)

call :probe_python
if errorlevel 1 (
    echo The new local Python environment does not start correctly.
    exit /b 1
)
exit /b 0

:probe_python
set "PY_CHECK=%TEMP%\steaimct_pycheck_%RANDOM%.txt"
"%PY%" -c "print('PYTHON_OK')" > "%PY_CHECK%" 2>nul
findstr /C:"PYTHON_OK" "%PY_CHECK%" >nul 2>nul
if errorlevel 1 (
    set "PROBE_RESULT=1"
) else (
    set "PROBE_RESULT=0"
)
del "%PY_CHECK%" >nul 2>nul
exit /b %PROBE_RESULT%

:probe_python_packages
set "PKG_CHECK=%TEMP%\steaimct_pkgcheck_%RANDOM%.txt"
"%PY%" -c "import docx, pypdf, reportlab; print('PACKAGES_OK')" > "%PKG_CHECK%" 2>nul
findstr /C:"PACKAGES_OK" "%PKG_CHECK%" >nul 2>nul
if errorlevel 1 (
    set "PROBE_RESULT=1"
) else (
    set "PROBE_RESULT=0"
)
del "%PKG_CHECK%" >nul 2>nul
exit /b %PROBE_RESULT%

:create_venv
echo Creating local Python environment...

if exist "%BUNDLED_PY%" (
    "%BUNDLED_PY%" -m venv "%VENV%"
    exit /b %ERRORLEVEL%
)

where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 -m venv "%VENV%" >nul 2>nul
    if not errorlevel 1 exit /b 0
    py -3.11 -m venv "%VENV%" >nul 2>nul
    if not errorlevel 1 exit /b 0
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m venv "%VENV%"
    exit /b %ERRORLEVEL%
)

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" -m venv "%VENV%"
    exit /b %ERRORLEVEL%
)

if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" (
    "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" -3.12 -m venv "%VENV%"
    exit /b %ERRORLEVEL%
)

call :download_python_installer
if errorlevel 1 exit /b 1

where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 -m venv "%VENV%" >nul 2>nul
    if not errorlevel 1 exit /b 0
    py -3.11 -m venv "%VENV%" >nul 2>nul
    if not errorlevel 1 exit /b 0
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m venv "%VENV%"
    exit /b %ERRORLEVEL%
)

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" -m venv "%VENV%"
    exit /b %ERRORLEVEL%
)

echo Python was installed, but this window cannot find it yet.
echo Please close this window, open the tutor folder again, and run start_tutor.bat.
exit /b 1

:download_python_installer
echo(
echo Python 3.12 is required before the tutor can start.
echo The official Python installer will now be downloaded.
echo When the installer opens:
echo   1. On the first installer screen, tick the checkbox at the bottom:
echo      "Add python.exe to PATH".
echo   2. Then select "Install Now".
echo   3. Wait until the installation has finished.
echo Then this launcher will continue automatically.
echo(
choice /C CN /N /M "Press C to continue with the Python download, or N to cancel: "
if errorlevel 2 (
    echo Python installation cancelled.
    exit /b 1
)

echo Downloading the official Python 3.12.10 installer...
if exist "%PYTHON_INSTALLER%" del /q "%PYTHON_INSTALLER%" >nul 2>nul
where curl.exe >nul 2>nul
if not errorlevel 1 (
    curl.exe -L --fail --retry 2 -o "%PYTHON_INSTALLER%" "%PYTHON_INSTALLER_URL%"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -UseBasicParsing -Uri '%PYTHON_INSTALLER_URL%' -OutFile '%PYTHON_INSTALLER%'"
)
if errorlevel 1 (
    echo Could not download Python automatically.
    echo Opening the official download page instead.
    start "" "https://www.python.org/downloads/windows/"
    exit /b 1
)
if not exist "%PYTHON_INSTALLER%" (
    echo The Python installer was not downloaded.
    start "" "https://www.python.org/downloads/windows/"
    exit /b 1
)

echo Starting the Python installer...
start /wait "" "%PYTHON_INSTALLER%"
if errorlevel 1 (
    echo The Python installer was cancelled or failed.
    exit /b 1
)
exit /b 0

:package_fail
echo(
echo Package installation failed.
echo Please check your internet connection and run start_tutor.bat again.
pause
exit /b 1

:fail
echo(
echo Startup failed. The tutor could not be started.
echo Please check the messages above.
echo Startup diagnostic: "%STARTUP_DIAGNOSTIC%"
pause
exit /b 1
