import json
import re
import sys
from datetime import datetime

import config


def redact_secrets(value):
    text = str(value or "")
    known_secrets = [config.MISTRAL_API_KEY]
    try:
        with open(config.MISTRAL_API_KEY_FILE, "r", encoding="utf-8") as key_file:
            known_secrets.append(key_file.read().strip())
    except OSError:
        pass

    for secret in known_secrets:
        if secret and len(secret) >= 8:
            text = text.replace(secret, "[REDACTED_API_KEY]")
    text = re.sub(r"(?i)(authorization\s*:\s*bearer\s+)[^\s,]+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)(MISTRAL_API_KEY\s*=\s*)[^\s,]+", r"\1[REDACTED]", text)
    return text


def ensure_log_files():
    for path in (config.ANALYSIS_LOG_FILE, config.MISTRAL_PROMPT_LOG_FILE):
        try:
            with open(path, "a", encoding="utf-8"):
                pass
        except OSError as error:
            _console_message(f"[logging] Unable to open log file {path}: {error}")


def _console_message(message):
    """Keep diagnostics visible on legacy Windows consoles without losing UTF-8 logs."""
    text = str(message or "")
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    safe_text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
    try:
        print(safe_text)
    except UnicodeEncodeError:
        # A redirected or unusual console stream may still reject its declared encoding.
        sys.stdout.buffer.write((text.encode("utf-8", errors="replace") + b"\n"))
        sys.stdout.buffer.flush()


def log_message(message):
    line = redact_secrets(message).rstrip("\n")
    _console_message(line)
    try:
        with open(config.ANALYSIS_LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(line + "\n")
    except OSError as error:
        _console_message(f"[logging] Unable to write analysis log: {error}")


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
    entry_lines = [redact_secrets(line) for line in entry_lines]
    entry_lines.append("")
    try:
        with open(config.MISTRAL_PROMPT_LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write("\n".join(entry_lines) + "\n")
    except OSError as error:
        _console_message(f"[logging] Unable to write prompt log: {error}")


ensure_log_files()
