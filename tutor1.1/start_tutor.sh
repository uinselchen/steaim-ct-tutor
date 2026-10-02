#!/bin/bash

export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

# Set root directory to the script's directory
ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP="$ROOT/app"
VENV="$APP/venv"
LOGFILE="$APP/data/outputs/server.log"
REQUIREMENTS="$APP/server/requirements.txt"
REQUIREMENTS_STAMP="$VENV/.requirements-installed"
KEY_FILE="$APP/server/mistral_api_key.txt"
TUTOR_URL="http://localhost:8000"

# List of directories to create
DIRS=(
    "app"
    "app/server"
    "app/frontend"
    "app/frontend/css"
    "app/frontend/js"
    "app/frontend/assets"
    "app/data"
    "app/data/curricula"
    "app/data/lessonplans"
    "app/data/templates"
    "app/data/outputs"
)

# Create directories if they don't exist
for D in "${DIRS[@]}"; do
    if [ ! -d "$ROOT/$D" ]; then
        mkdir -p "$ROOT/$D"
    fi
done

# Check and create virtual environment if it doesn't exist
if [ ! -f "$VENV/bin/python" ]; then
    if ! command -v python3 >/dev/null 2>&1; then
        echo "Python 3 is required to start the tutor."
        if [ "$(uname -s)" = "Darwin" ]; then
            echo "Install Python 3.12 from https://www.python.org/downloads/macos/"
            echo "On macOS, download the macOS 64-bit universal installer."
            echo "Then run start_tutor.command again."
            if command -v open >/dev/null 2>&1; then
                open "https://www.python.org/downloads/macos/"
            fi
        else
            echo "Install Python 3.11 or newer from https://www.python.org/downloads/"
            echo "Then run this launcher again."
            if command -v xdg-open >/dev/null 2>&1; then
                xdg-open "https://www.python.org/downloads/" >/dev/null 2>&1 &
            fi
        fi
        read -r -p "Press [Enter] to continue..."
        exit 1
    fi
    echo "Creating local virtual environment..."
    python3 -m venv "$VENV" 2>/dev/null
    if [ ! -f "$VENV/bin/python" ]; then
        echo "Failed to create local virtual environment."
        echo "Please install Python 3 and make it available on PATH."
        read -p "Press [Enter] to continue..."
        exit 1
    fi
fi

# Install runtime dependencies on the first start and after requirements change.
if [ ! -f "$REQUIREMENTS_STAMP" ] || [ "$REQUIREMENTS" -nt "$REQUIREMENTS_STAMP" ]; then
    echo "Installing Python dependencies..."
    "$VENV/bin/python" -m pip install -r "$REQUIREMENTS"
    if [ "$?" -ne 0 ]; then
        echo "Failed to install Python dependencies."
        echo "Check your internet connection and the requirements file: $REQUIREMENTS"
        read -p "Press [Enter] to continue..."
        exit 1
    fi
    touch "$REQUIREMENTS_STAMP"
fi

# Keep the API key local. It is entered through Admin settings and is ignored by Git.
if [ ! -f "$KEY_FILE" ]; then
    touch "$KEY_FILE"
fi
if [ ! -s "$KEY_FILE" ]; then
    echo "WARNING: No Mistral API key configured."
    echo "Open Admin settings and enter the key; it will be saved locally to $KEY_FILE."
fi

echo "Starting local tutor..."
echo "Logging server output to $LOGFILE"

open_tutor_browser() {
    (
        for _ in $(seq 1 30); do
            if command -v curl >/dev/null 2>&1 && curl -fsS "$TUTOR_URL" >/dev/null 2>&1; then
                if [ "$(uname -s)" = "Darwin" ] && command -v open >/dev/null 2>&1; then
                    open "$TUTOR_URL"
                elif command -v xdg-open >/dev/null 2>&1; then
                    xdg-open "$TUTOR_URL" >/dev/null 2>&1
                fi
                exit 0
            fi
            sleep 1
        done
    ) &
}

# Activate the virtual environment
source "$VENV/bin/activate"

# Change to the server directory and run the app
cd "$APP/server" || exit 1
echo "==== $(date) ====" > "$LOGFILE"
open_tutor_browser
python -X utf8 app.py >> "$LOGFILE" 2>&1
EXIT_CODE=$?

# Return to the original directory
cd - || exit 1

if [ "$EXIT_CODE" -ne 0 ]; then
    echo
    echo "The tutor stopped with error code $EXIT_CODE."
    echo "Check the message above for details."
    echo "See $LOGFILE for the full server log."
    read -p "Press [Enter] to continue..."
fi
