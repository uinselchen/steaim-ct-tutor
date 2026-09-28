import os

from config_utils import parse_bool_value

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, ".."))
FRONTEND_ROOT = os.path.join(APP_ROOT, "frontend")
DATA_ROOT = os.path.join(APP_ROOT, "data")
PROMPTS_ROOT = os.path.join(HERE, "prompts")
CURRICULA_ROOT = os.path.join(DATA_ROOT, "curricula")
AMENDMENTS_ROOT = os.path.join(DATA_ROOT, "amendments")
LESSONPLANS_ROOT = os.path.join(DATA_ROOT, "lessonplans")
TEMPLATES_ROOT = os.path.join(DATA_ROOT, "templates")
CONFIG_FILE = os.path.join(DATA_ROOT, "config.json")
ENV_FILE = os.path.join(HERE, ".env")
MISTRAL_API_KEY_FILE = os.path.join(HERE, "mistral_api_key.txt")
OUTPUT_ROOT = os.path.join(DATA_ROOT, "outputs")
ANALYSIS_LOG_FILE = os.path.join(OUTPUT_ROOT, "analysis-log.txt")
MISTRAL_PROMPT_LOG_FILE = os.path.join(OUTPUT_ROOT, "mistral-prompt-log.txt")
STEP3_STATE_ROOT = os.path.join(OUTPUT_ROOT, "step3-sessions")
EXPORTS_ROOT = os.path.join(OUTPUT_ROOT, "exports")

DEFAULT_MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
DEFAULT_MISTRAL_MODEL = "mistral-small-latest"
DEFAULT_SMTP_PORT = 587
DEFAULT_SMTP_USE_TLS = True
DEFAULT_SMTP_USE_SSL = False

MISTRAL_API_KEY = None
MISTRAL_API_URL = DEFAULT_MISTRAL_API_URL
MISTRAL_MODEL = DEFAULT_MISTRAL_MODEL
MISTRAL_ANALYSIS_TIMEOUT = 180
MISTRAL_REFINEMENT_TIMEOUT = 120
MISTRAL_TEST_TIMEOUT = 30
SMTP_HOST = None
SMTP_PORT = DEFAULT_SMTP_PORT
SMTP_USERNAME = None
SMTP_PASSWORD = None
SMTP_USE_TLS = DEFAULT_SMTP_USE_TLS
SMTP_USE_SSL = DEFAULT_SMTP_USE_SSL
MAIL_FROM_ADDRESS = None
MAIL_TO_ADDRESS = None

PORT = 8000


def ensure_directories():
    """Create the local folders and key file required by the tutor."""
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


def _reset_config_values():
    global MISTRAL_API_KEY, MISTRAL_API_URL, MISTRAL_MODEL, SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD
    global SMTP_USE_TLS, SMTP_USE_SSL, MAIL_FROM_ADDRESS, MAIL_TO_ADDRESS

    MISTRAL_API_KEY = None
    MISTRAL_API_URL = DEFAULT_MISTRAL_API_URL
    MISTRAL_MODEL = DEFAULT_MISTRAL_MODEL
    SMTP_HOST = None
    SMTP_PORT = DEFAULT_SMTP_PORT
    SMTP_USERNAME = None
    SMTP_PASSWORD = None
    SMTP_USE_TLS = DEFAULT_SMTP_USE_TLS
    SMTP_USE_SSL = DEFAULT_SMTP_USE_SSL
    MAIL_FROM_ADDRESS = None
    MAIL_TO_ADDRESS = None


def _read_local_api_key():
    try:
        with open(MISTRAL_API_KEY_FILE, "r", encoding="utf-8") as key_file:
            return key_file.read().strip() or None
    except (OSError, UnicodeError) as error:
        print(f"[config] Unable to read the local API key file: {error}")
        return None


def _apply_env_value(key, value, source):
    global MISTRAL_API_URL, MISTRAL_MODEL, SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD
    global SMTP_USE_TLS, SMTP_USE_SSL, MAIL_FROM_ADDRESS, MAIL_TO_ADDRESS

    if not value:
        return
    if key == "MISTRAL_API_URL":
        MISTRAL_API_URL = value
    elif key == "MISTRAL_MODEL":
        MISTRAL_MODEL = value
    elif key == "SMTP_HOST":
        SMTP_HOST = value
    elif key == "SMTP_PORT":
        try:
            SMTP_PORT = int(value)
        except (TypeError, ValueError):
            SMTP_PORT = DEFAULT_SMTP_PORT
            print(f"[config] Invalid SMTP_PORT in {source}; using {DEFAULT_SMTP_PORT}.")
    elif key == "SMTP_USERNAME":
        SMTP_USERNAME = value
    elif key == "SMTP_PASSWORD":
        SMTP_PASSWORD = value
    elif key == "SMTP_USE_TLS":
        SMTP_USE_TLS = parse_bool_value(value, default=DEFAULT_SMTP_USE_TLS)
    elif key == "SMTP_USE_SSL":
        SMTP_USE_SSL = parse_bool_value(value, default=DEFAULT_SMTP_USE_SSL)
    elif key == "MAIL_FROM_ADDRESS":
        MAIL_FROM_ADDRESS = value
    elif key == "MAIL_TO_ADDRESS":
        MAIL_TO_ADDRESS = value


def _load_env_file_values():
    global MISTRAL_API_KEY

    if not os.path.exists(ENV_FILE):
        return
    try:
        with open(ENV_FILE, "r", encoding="utf-8") as env_file:
            for line_number, raw_line in enumerate(env_file, start=1):
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key == "MISTRAL_API_KEY":
                    if value and value != "your_mistral_api_key_here" and not MISTRAL_API_KEY:
                        MISTRAL_API_KEY = value
                else:
                    _apply_env_value(key, value, f"{ENV_FILE}:{line_number}")
    except (OSError, UnicodeError) as error:
        print(f"[config] Unable to read .env file {ENV_FILE}: {error}")


def _load_process_environment_values():
    global MISTRAL_API_KEY

    environment_key = os.environ.get("MISTRAL_API_KEY")
    if not MISTRAL_API_KEY and environment_key and environment_key != "your_mistral_api_key_here":
        MISTRAL_API_KEY = environment_key
    for key in (
        "MISTRAL_API_URL",
        "MISTRAL_MODEL",
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
        "SMTP_USE_TLS",
        "SMTP_USE_SSL",
        "MAIL_FROM_ADDRESS",
        "MAIL_TO_ADDRESS",
    ):
        _apply_env_value(key, os.environ.get(key), "the process environment")


def load_env_file():
    """Load local-file settings first, then apply process environment overrides."""
    global MISTRAL_API_KEY

    _reset_config_values()
    MISTRAL_API_KEY = _read_local_api_key()
    _load_env_file_values()
    _load_process_environment_values()


ensure_directories()
