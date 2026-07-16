import json
from datetime import datetime

import config


def ensure_log_files():
    for path in (config.ANALYSIS_LOG_FILE, config.MISTRAL_PROMPT_LOG_FILE):
        try:
            with open(path, "a", encoding="utf-8"):
                pass
        except OSError:
            raise


def log_message(message):
    line = message.rstrip("\n")
    print(line)
    with open(config.ANALYSIS_LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(line + "\n")


def log_mistral_prompt(label, system_prompt, user_prompt, request_body=None):
    timestamp = datetime.now().isoformat(timespec="seconds")
    entry_lines = [
        "=" * 80,
        f"[{timestamp}] {label}",
        "",
        "SYSTEM PROMPT:",
        str(system_prompt or "").rstrip(),
        "",
        "USER PROMPT:",
        str(user_prompt or "").rstrip(),
    ]
    if request_body is not None:
        entry_lines.extend([
            "",
            "REQUEST BODY:",
            json.dumps(request_body, ensure_ascii=False, indent=2),
        ])
    entry_lines.append("")
    with open(config.MISTRAL_PROMPT_LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write("\n".join(entry_lines) + "\n")


ensure_log_files()
