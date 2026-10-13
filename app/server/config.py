import os
import sys
from config_utils import parse_bool_value

#TODO: Remove - This is local pathing. Don't believe it does anything on any other machine.
RUNTIME_PYTHON_PACKAGES = r"C:\Users\Uinsel\.cache\codex-runtimes\codex-primary-runtime\dependencies\python"
if os.path.isdir(RUNTIME_PYTHON_PACKAGES) and RUNTIME_PYTHON_PACKAGES not in sys.path:
    sys.path.insert(0, RUNTIME_PYTHON_PACKAGES)

# Collect project directory paths
HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, ".."))
FRONTEND_ROOT = os.path.join(APP_ROOT, "frontend")
DATA_ROOT = os.path.join(APP_ROOT, "data")
PROMPTS_ROOT = os.path.join(HERE, "prompts")
CURRICULA_ROOT = os.path.join(DATA_ROOT, "curricula")
AMENDMENTS_ROOT = os.path.join(DATA_ROOT, "amendments")
LESSONPLANS_ROOT = os.path.join(DATA_ROOT, "lessonplans")
TEMPLATES_ROOT = os.path.join(APP_ROOT, "templates")
CONFIG_FILE = os.path.join(DATA_ROOT, "config.json")
ENV_FILE = os.path.join(HERE, ".env")
MISTRAL_API_KEY_FILE = os.path.join(HERE, "mistral_api_key.txt")
OUTPUT_ROOT = os.path.join(DATA_ROOT, "outputs")
ANALYSIS_LOG_FILE = os.path.join(OUTPUT_ROOT, "analysis-log.txt")
MISTRAL_PROMPT_LOG_FILE = os.path.join(OUTPUT_ROOT, "mistral-prompt-log.txt")
STEP3_STATE_ROOT = os.path.join(OUTPUT_ROOT, "step3-sessions")
EXPORTS_ROOT = os.path.join(OUTPUT_ROOT, "exports")

# Config Mistral
MISTRAL_API_KEY = None
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_MODEL = "mistral-small-latest"
MISTRAL_ANALYSIS_TIMEOUT = 180
MISTRAL_REFINEMENT_TIMEOUT = 120
MISTRAL_TEST_TIMEOUT = 30
# Config Mailing
SMTP_HOST = None
SMTP_PORT = 587
SMTP_USERNAME = None
SMTP_PASSWORD = None
SMTP_USE_TLS = True
SMTP_USE_SSL = False
MAIL_FROM_ADDRESS = None
MAIL_TO_ADDRESS = None
# Config Localhost
PORT = 8000


def ensure_directories():
    """
    Creates necessary directories and files, if they don't exist.
    """
    for path in (
        FRONTEND_ROOT,
        CURRICULA_ROOT,
        AMENDMENTS_ROOT,
        LESSONPLANS_ROOT,
        TEMPLATES_ROOT,
        OUTPUT_ROOT,
        STEP3_STATE_ROOT,
        EXPORTS_ROOT,
    ):
        os.makedirs(path, exist_ok=True)
    if not os.path.exists(MISTRAL_API_KEY_FILE):
        with open(MISTRAL_API_KEY_FILE, "w", encoding="utf-8"):
            pass


def load_env_file():
    """
    Loads Mistral and mailing configs.
    """
    global MISTRAL_API_KEY, MISTRAL_API_URL, MISTRAL_MODEL, SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD
    global SMTP_USE_TLS, SMTP_USE_SSL, MAIL_FROM_ADDRESS, MAIL_TO_ADDRESS

    MISTRAL_API_KEY = None
    try:
        with open(MISTRAL_API_KEY_FILE, "r", encoding="utf-8") as key_file:
            MISTRAL_API_KEY = key_file.read().strip() or None
    except OSError:
        pass
        #TODO: Maybe we should add some Error handling here, such as an Error message/popup

    # Load configs from ENV_FILE
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                # Skip lines without valid key-value pairs
                if not line or line.startswith("#") or "=" not in line:
                    continue
                # Extract key-value pairs. Skip invalid.
                key, value = line.split("=", 1)
                value = value.strip().strip('"').strip("'")
                if not value or key not in globals():
                    continue

                # Key is a special case
                if key!="MISTRAL_API_KEY" or value == "your_mistral_api_key_here" or MISTRAL_API_KEY:
                    continue
                # Write value into global constant
                globals()[key] = value

    # Load configs from local OS environment
    environment_key = os.environ.get("MISTRAL_API_KEY")
    if not MISTRAL_API_KEY and environment_key and environment_key != "your_mistral_api_key_here":
        MISTRAL_API_KEY = environment_key
    for key in ["MISTRAL_API_URL",
                "MISTRAL_MODEL",
                "SMTP_HOST",
                "SMTP_PORT",
                "SMTP_USERNAME",
                "SMTP_PASSWORD",
                "SMTP_USE_TLS",
                "SMTP_USE_SSL",
                "MAIL_FROM_ADDRESS",
                "MAIL_TO_ADDRESS"]:
        if os.environ.get(key):
            globals()[key] = os.environ[key]

    # Convert non-string-valued configs
    try:
        SMTP_PORT = int(SMTP_PORT)
    except ValueError:
        SMTP_PORT = 587
    SMTP_USE_TLS = parse_bool_value(SMTP_USE_TLS)
    SMTP_USE_SSL = parse_bool_value(SMTP_USE_SSL)


ensure_directories()
