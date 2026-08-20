import os
import sys


RUNTIME_PYTHON_PACKAGES = r"C:\Users\Uinsel\.cache\codex-runtimes\codex-primary-runtime\dependencies\python"
if os.path.isdir(RUNTIME_PYTHON_PACKAGES) and RUNTIME_PYTHON_PACKAGES not in sys.path:
    sys.path.insert(0, RUNTIME_PYTHON_PACKAGES)

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, ".."))
FRONTEND_ROOT = os.path.join(APP_ROOT, "frontend")
DATA_ROOT = os.path.join(APP_ROOT, "data")
PROMPTS_ROOT = os.path.join(HERE, "prompts")
CURRICULA_ROOT = os.path.join(DATA_ROOT, "curricula")
AMENDMENTS_ROOT = os.path.join(DATA_ROOT, "amendments")
LESSONPLANS_ROOT = os.path.join(DATA_ROOT, "lessonplans")
CONFIG_FILE = os.path.join(DATA_ROOT, "config.json")
ENV_FILE = os.path.join(HERE, ".env")
OUTPUT_ROOT = os.path.join(DATA_ROOT, "outputs")
ANALYSIS_LOG_FILE = os.path.join(OUTPUT_ROOT, "analysis-log.txt")
MISTRAL_PROMPT_LOG_FILE = os.path.join(OUTPUT_ROOT, "mistral-prompt-log.txt")
STEP3_STATE_ROOT = os.path.join(OUTPUT_ROOT, "step3-sessions")
EXPORTS_ROOT = os.path.join(OUTPUT_ROOT, "exports")

MISTRAL_API_KEY = None
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_MODEL = "mistral-small-latest"
MISTRAL_ANALYSIS_TIMEOUT = 180
MISTRAL_REFINEMENT_TIMEOUT = 120
MISTRAL_TEST_TIMEOUT = 30
SMTP_HOST = None
SMTP_PORT = 587
SMTP_USERNAME = None
SMTP_PASSWORD = None
SMTP_USE_TLS = True
SMTP_USE_SSL = False
MAIL_FROM_ADDRESS = None
MAIL_TO_ADDRESS = None

PORT = 8000


def ensure_directories():
    for path in (
        FRONTEND_ROOT,
        CURRICULA_ROOT,
        AMENDMENTS_ROOT,
        LESSONPLANS_ROOT,
        os.path.join(DATA_ROOT, "templates"),
        OUTPUT_ROOT,
        STEP3_STATE_ROOT,
        EXPORTS_ROOT,
    ):
        os.makedirs(path, exist_ok=True)


def load_env_file():
    global MISTRAL_API_KEY, MISTRAL_API_URL, MISTRAL_MODEL, SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD
    global SMTP_USE_TLS, SMTP_USE_SSL, MAIL_FROM_ADDRESS, MAIL_TO_ADDRESS

    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                value = value.strip().strip('"').strip("'")
                if key == "MISTRAL_API_KEY" and value:
                    MISTRAL_API_KEY = value
                elif key == "MISTRAL_API_URL" and value:
                    MISTRAL_API_URL = value
                elif key == "MISTRAL_MODEL" and value:
                    MISTRAL_MODEL = value
                elif key == "SMTP_HOST" and value:
                    SMTP_HOST = value
                elif key == "SMTP_PORT" and value:
                    try:
                        SMTP_PORT = int(value)
                    except ValueError:
                        SMTP_PORT = 587
                elif key == "SMTP_USERNAME" and value:
                    SMTP_USERNAME = value
                elif key == "SMTP_PASSWORD" and value:
                    SMTP_PASSWORD = value
                elif key == "SMTP_USE_TLS" and value:
                    SMTP_USE_TLS = value.lower() in ("1", "true", "yes", "on")
                elif key == "SMTP_USE_SSL" and value:
                    SMTP_USE_SSL = value.lower() in ("1", "true", "yes", "on")
                elif key == "MAIL_FROM_ADDRESS" and value:
                    MAIL_FROM_ADDRESS = value
                elif key == "MAIL_TO_ADDRESS" and value:
                    MAIL_TO_ADDRESS = value

    if not MISTRAL_API_KEY:
        MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
    if os.environ.get("MISTRAL_API_URL"):
        MISTRAL_API_URL = os.environ["MISTRAL_API_URL"]
    if os.environ.get("MISTRAL_MODEL"):
        MISTRAL_MODEL = os.environ["MISTRAL_MODEL"]
    if os.environ.get("SMTP_HOST"):
        SMTP_HOST = os.environ["SMTP_HOST"]
    if os.environ.get("SMTP_PORT"):
        try:
            SMTP_PORT = int(os.environ["SMTP_PORT"])
        except ValueError:
            SMTP_PORT = 587
    if os.environ.get("SMTP_USERNAME"):
        SMTP_USERNAME = os.environ["SMTP_USERNAME"]
    if os.environ.get("SMTP_PASSWORD"):
        SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]
    if os.environ.get("SMTP_USE_TLS"):
        SMTP_USE_TLS = os.environ["SMTP_USE_TLS"].lower() in ("1", "true", "yes", "on")
    if os.environ.get("SMTP_USE_SSL"):
        SMTP_USE_SSL = os.environ["SMTP_USE_SSL"].lower() in ("1", "true", "yes", "on")
    if os.environ.get("MAIL_FROM_ADDRESS"):
        MAIL_FROM_ADDRESS = os.environ["MAIL_FROM_ADDRESS"]
    if os.environ.get("MAIL_TO_ADDRESS"):
        MAIL_TO_ADDRESS = os.environ["MAIL_TO_ADDRESS"]


ensure_directories()
