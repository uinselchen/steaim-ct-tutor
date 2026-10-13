import json
import re


def parse_subjects_value(value):
    if not value:
        return []
    if isinstance(value, list):
        values = value
    else:
        text = str(value).strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            values = parsed if isinstance(parsed, list) else [parsed]
        except Exception:
            values = [part.strip() for part in re.split(r"[;,]", text)]

    cleaned = []
    for item in values:
        item_text = str(item or "").strip()
        if item_text and item_text not in cleaned:
            cleaned.append(item_text)
    return cleaned


def build_conversation_text(conversation):
    conversation = conversation if isinstance(conversation, list) else []
    lines = []
    for message in conversation:
        message = message if isinstance(message, dict) else {}
        role = str(message.get("role", "tutor")).strip() or "tutor"
        text = str(message.get("text", "")).strip()
        time = str(message.get("time", "")).strip()
        prefix = f"[{time}] {role}: " if time else f"{role}: "
        lines.append(prefix + text)
    return "\n".join(lines).strip()
