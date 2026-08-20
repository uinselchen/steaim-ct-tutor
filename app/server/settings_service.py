import os

import config


DEFAULT_MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
PROMPT_FILENAMES = [
    "analysis_system_prompt.txt",
    "refinement_system_prompt.txt",
    "mistral_test_system_prompt.txt",
]


def relative_path(path):
    try:
        return os.path.relpath(path, config.APP_ROOT).replace("\\", "/")
    except ValueError:
        return path


def read_env_values(path=None):
    env_path = path or config.ENV_FILE
    values = {}
    if not os.path.exists(env_path):
        return values
    with open(env_path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def write_env_values(updates, path=None):
    env_path = path or config.ENV_FILE
    updates = updates if isinstance(updates, dict) else {}
    existing_lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as env_file:
            existing_lines = env_file.read().splitlines()

    written_keys = set()
    next_lines = []
    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            next_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in updates:
            next_lines.append(f"{key}={updates[key]}")
            written_keys.add(key)
        else:
            next_lines.append(line)

    for key, value in updates.items():
        if key not in written_keys:
            next_lines.append(f"{key}={value}")

    os.makedirs(os.path.dirname(env_path), exist_ok=True)
    with open(env_path, "w", encoding="utf-8") as env_file:
        env_file.write("\n".join(next_lines).rstrip() + "\n")


def build_settings_status():
    prompt_paths = []
    for filename in PROMPT_FILENAMES:
        absolute_path = os.path.join(config.PROMPTS_ROOT, filename)
        prompt_paths.append({
            "name": filename,
            "relativePath": relative_path(absolute_path),
            "exists": os.path.exists(absolute_path),
        })

    email_configured = bool(config.SMTP_HOST and config.SMTP_USERNAME and config.SMTP_PASSWORD and config.MAIL_TO_ADDRESS)
    return {
        "mistral": {
            "configured": bool(config.MISTRAL_API_KEY),
            "apiUrl": config.MISTRAL_API_URL,
            "model": config.MISTRAL_MODEL,
            "apiKeyConfigured": bool(config.MISTRAL_API_KEY),
        },
        "email": {
            "configured": email_configured,
            "sender": config.MAIL_FROM_ADDRESS or config.SMTP_USERNAME or "",
            "recipient": config.MAIL_TO_ADDRESS or "",
        },
        "paths": {
            "curriculaRoot": relative_path(config.CURRICULA_ROOT) if os.path.isdir(config.CURRICULA_ROOT) else "",
            "outputRoot": relative_path(config.OUTPUT_ROOT) if os.path.isdir(config.OUTPUT_ROOT) else "",
        },
        "prompts": prompt_paths,
    }


def update_mistral_settings(data):
    data = data if isinstance(data, dict) else {}
    api_url = str(data.get("mistralApiUrl", "")).strip()
    model = str(data.get("mistralModel", "")).strip()
    api_key = str(data.get("mistralApiKey", "")).strip()

    updates = {}
    if api_url:
        updates["MISTRAL_API_URL"] = api_url
    if model:
        updates["MISTRAL_MODEL"] = model
    if api_key:
        updates["MISTRAL_API_KEY"] = api_key

    if not updates:
        return {"error": "No settings provided"}

    write_env_values(updates)
    config.load_env_file()
    return {
        "saved": True,
        "updated": sorted(updates.keys()),
        "status": build_settings_status(),
    }
