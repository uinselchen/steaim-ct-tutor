import json
import os
import traceback

import config
import mistral_service
from logging_utils import log_message
from text_utils import build_conversation_text


def step3_state_path(session_id):
    session = str(session_id or "").strip()
    if not session:
        return ""
    return os.path.join(config.STEP3_STATE_ROOT, f"{session}.json")


def step3_conversation_log_path(session_id):
    session = str(session_id or "").strip()
    if not session:
        return ""
    return os.path.join(config.STEP3_STATE_ROOT, f"{session}-conversation.txt")


def save_step3_state(session_id, state):
    path = step3_state_path(session_id)
    if not path:
        return False
    try:
        with open(path, "w", encoding="utf-8") as state_file:
            json.dump(state, state_file, ensure_ascii=False, indent=2)
        return True
    except OSError:
        log_message(f"[step3-state] Unable to save session={session_id}")
        log_message(traceback.format_exc())
        return False


def load_step3_state(session_id):
    path = step3_state_path(session_id)
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as state_file:
            return json.load(state_file)
    except Exception:
        log_message(f"[step3-state] Unable to load session={session_id}")
        log_message(traceback.format_exc())
        return None


def save_step3_conversation_log(session_id, conversation, payload, result):
    path = step3_conversation_log_path(session_id)
    if not path:
        return False
    try:
        draft = None
        if isinstance(result, dict) and isinstance(result.get("updated_draft"), dict):
            draft = result.get("updated_draft")
        elif isinstance(payload, dict) and isinstance(payload.get("draft"), dict):
            draft = payload.get("draft")

        memory_summary = mistral_service.build_step3_memory_summary(payload, conversation, draft)
        conversation_text = build_conversation_text(conversation)
        content = [
            memory_summary,
            "",
            "=" * 72,
            "Full conversation log",
            "=" * 72,
            conversation_text or "(no conversation yet)",
            "",
        ]
        with open(path, "w", encoding="utf-8") as log_file:
            log_file.write("\n".join(content))
        return True
    except OSError:
        log_message(f"[step3-conversation-log] Unable to save session={session_id}")
        log_message(traceback.format_exc())
        return False
