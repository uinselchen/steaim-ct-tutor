import json
import json
import re
import traceback
import urllib.error
import urllib.request

import config
from logging_utils import log_message, log_mistral_prompt
from prompts import load_prompt_file
from text_utils import build_conversation_text, parse_subjects_value


def get_step3_focus_label(payload):
    current_node = payload.get("currentNode") if isinstance(payload.get("currentNode"), dict) else {}
    focus_title = str(current_node.get("pointTitle", "")).strip()
    focus_label = str(current_node.get("label", "")).strip()
    focus_id = str(current_node.get("id", "")).strip()
    focus_parts = [item for item in (focus_label, focus_title, focus_id) if item]
    return " - ".join(focus_parts) if focus_parts else "No active focus"


def summarize_step3_changes(draft):
    draft = draft if isinstance(draft, dict) else {}
    changes = draft.get("changes") if isinstance(draft.get("changes"), list) else []
    lines = []
    for index, change in enumerate(changes[-8:], start=1):
        change = change if isinstance(change, dict) else {}
        title = str(change.get("title") or change.get("kind") or "Change").strip()
        reason = str(change.get("reason", "")).strip()
        before_value = str(change.get("beforeValue", "")).strip()
        after_value = str(change.get("afterValue", "")).strip()
        before_after = ""
        if before_value or after_value:
            before_after = f" ({before_value or '?'} -> {after_value or '?'})"
        line = f"{index}. {title}{before_after}"
        if reason:
            line += f": {reason}"
        lines.append(line)
    return lines


def build_step3_memory_summary(payload, conversation=None, draft=None):
    payload = payload if isinstance(payload, dict) else {}
    draft = draft if isinstance(draft, dict) else payload.get("draft")
    draft = draft if isinstance(draft, dict) else {}
    conversation = conversation if isinstance(conversation, list) else payload.get("conversation")
    conversation = conversation if isinstance(conversation, list) else []

    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    subjects = payload.get("subjects") if isinstance(payload.get("subjects"), list) else meta.get("subjects")
    subjects = subjects if isinstance(subjects, list) else []
    latest_teacher_reply = str(payload.get("userMessage", "")).strip()
    current_focus = get_step3_focus_label(payload)
    changes = summarize_step3_changes(draft)
    recent_conversation = build_conversation_text(conversation[-10:])

    lines = [
        "Step 3 local memory summary",
        f"Session: {payload.get('sessionId', '') or 'unknown'}",
        f"Country: {payload.get('country') or meta.get('country') or 'unknown'}",
        f"Subjects: {', '.join(str(item) for item in subjects) if subjects else 'unknown'}",
        f"Current focus: {current_focus}",
        f"Latest teacher reply: {latest_teacher_reply or '(none)'}",
        "",
        "Decisions and changes already applied:",
    ]
    lines.extend(changes if changes else ["(none yet)"])
    lines.extend([
        "",
        "Recent conversation:",
        recent_conversation or "(no conversation yet)",
        "",
        "Instruction for the next answer:",
        "Treat the recent conversation and applied changes as memory. Do not contradict them. "
        "If the teacher challenges a previous suggestion, acknowledge it and continue from the saved context.",
    ])
    return "\n".join(lines).strip()


def extract_json_block(text):
    if not text:
        return ""

    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    start = cleaned.find("{")
    if start == -1:
        return ""

    in_string = False
    escape = False
    depth = 0
    end = None

    for index in range(start, len(cleaned)):
        char = cleaned[index]
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break

    if end is None:
        return cleaned[start:].strip()
    return cleaned[start:end].strip()


def repair_json_quotes(text):
    if not text:
        return text

    repaired = []
    in_string = False
    escape = False

    for index, char in enumerate(text):
        if escape:
            repaired.append(char)
            escape = False
            continue

        if char == "\\":
            repaired.append(char)
            if in_string:
                escape = True
            continue

        if char == '"':
            if not in_string:
                in_string = True
                repaired.append(char)
                continue

            next_index = index + 1
            while next_index < len(text) and text[next_index].isspace():
                next_index += 1
            next_char = text[next_index] if next_index < len(text) else ""

            if next_char in (",", "}", "]", "", ":"):
                in_string = False
                repaired.append(char)
            else:
                repaired.append("\\\"")
            continue

        repaired.append(char)

    return "".join(repaired)


def repair_json_common_mistakes(text):
    if not text:
        return text

    repaired = text
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    repaired = re.sub(r"\bNone\b", "null", repaired)
    repaired = re.sub(r"\bTrue\b", "true", repaired)
    repaired = re.sub(r"\bFalse\b", "false", repaired)
    repaired = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_-]*)(\s*:)", r'\1"\2"\3', repaired)
    return repaired


def parse_json_response_block(text):
    raw_block = extract_json_block(text)
    if not raw_block:
        return None, None

    candidates = [raw_block]
    quote_repaired = repair_json_quotes(raw_block)
    common_repaired = repair_json_common_mistakes(raw_block)
    combined_repaired = repair_json_common_mistakes(quote_repaired)

    for candidate in (quote_repaired, common_repaired, combined_repaired):
        if candidate != raw_block and candidate not in candidates:
            candidates.append(candidate)

    first_error = None
    for candidate in candidates:
        try:
            return json.loads(candidate), candidate
        except json.JSONDecodeError as error:
            if first_error is None:
                first_error = error
            continue

    if first_error:
        position = first_error.pos
        start = max(0, position - 220)
        end = min(len(raw_block), position + 220)
        log_message(f"[mistral] JSON parse error context: {raw_block[start:end]}")
        raise first_error
    raise ValueError("Unable to parse JSON response")


def build_mistral_request_body(system_prompt, user_prompt):
    return {
        "model": config.MISTRAL_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }


def post_mistral_chat_completion(request_body, timeout):
    request = urllib.request.Request(
        config.MISTRAL_API_URL,
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.MISTRAL_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def repair_mistral_json_with_model(content, label, timeout):
    repair_system_prompt = (
        "You repair invalid JSON. Return only one valid raw JSON object. "
        "Do not add markdown, explanations, comments, or code fences. "
        "Preserve all keys and values when possible."
    )
    repair_user_prompt = "Repair this invalid JSON into valid JSON:\n" + str(content or "")
    request_body = build_mistral_request_body(repair_system_prompt, repair_user_prompt)
    log_mistral_prompt(f"{label}-json-repair", repair_system_prompt, repair_user_prompt, request_body)

    try:
        response_data = post_mistral_chat_completion(request_body, timeout)
        repair_content = response_data["choices"][0]["message"]["content"]
        log_message(f"[{label}] JSON repair response received")
        parsed, json_block = parse_json_response_block(repair_content)
        if json_block and isinstance(parsed, dict):
            return parsed
    except Exception as error:
        log_message(f"[{label}] JSON repair failed: {error}")
        log_message(traceback.format_exc())
    return None


def parse_mistral_json_content(content, label, timeout):
    try:
        parsed, json_block = parse_json_response_block(content)
        if not json_block:
            return {"error": "Mistral did not return a JSON block", "raw": content}
        if isinstance(parsed, dict):
            return parsed
        return {"error": "Mistral did not return a JSON object", "raw": json_block}
    except Exception as error:
        log_message(f"[{label}] Could not parse response locally: {error}")
        repaired = repair_mistral_json_with_model(content, label, timeout)
        if repaired:
            return repaired
        return {"error": f"Could not parse Mistral response as JSON: {error}", "raw": content}


def maybe_retry_without_response_format(request_body, timeout, label):
    response_format = request_body.pop("response_format", None)
    if response_format is None:
        return post_mistral_chat_completion(request_body, timeout)
    try:
        log_message(f"[{label}] Retrying without response_format")
        return post_mistral_chat_completion(request_body, timeout)
    finally:
        request_body["response_format"] = response_format


def format_context_range(from_value, to_value, unknown_label="not provided"):
    start = str(from_value or "").strip()
    end = str(to_value or "").strip()
    if start and end:
        return f"{start} to {end}"
    if start:
        return f"{start} to ?"
    if end:
        return f"? to {end}"
    return unknown_label


def build_ui_target_context(metadata):
    subjects = metadata.get("subjects", [])
    if isinstance(subjects, str):
        subjects = parse_subjects_value(subjects)
    return {
        "country": str(metadata.get("country", "")).strip(),
        "subjects": subjects,
        "gradeRange": {
            "from": str(metadata.get("gradeFrom", "")).strip(),
            "to": str(metadata.get("gradeTo", "")).strip(),
            "display": format_context_range(metadata.get("gradeFrom", ""), metadata.get("gradeTo", "")),
        },
        "ageRange": {
            "from": str(metadata.get("ageFrom", "")).strip(),
            "to": str(metadata.get("ageTo", "")).strip(),
            "display": format_context_range(metadata.get("ageFrom", ""), metadata.get("ageTo", "")),
        },
        "specifics": str(metadata.get("specifics", "")).strip(),
        "priority": "Use this teacher-entered UI context as the intended lesson context. Check the uploaded document against it.",
    }


def build_analysis_context_summary(payload):
    context = payload.get("ui_target_context") if isinstance(payload.get("ui_target_context"), dict) else {}
    subjects = context.get("subjects") if isinstance(context.get("subjects"), list) else []
    grade_range = context.get("gradeRange") if isinstance(context.get("gradeRange"), dict) else {}
    age_range = context.get("ageRange") if isinstance(context.get("ageRange"), dict) else {}
    language = context.get("language") if isinstance(context.get("language"), dict) else "English"
    lines = [
        "Teacher-entered UI target context (read this first):",
        f"- Country: {context.get('country') or 'not provided'}",
        f"- Subject(s): {', '.join(subjects) if subjects else 'not provided'}",
        f"- Intended grade range: {grade_range.get('display') or 'not provided'}",
        f"- Intended age range: {age_range.get('display') or 'not provided'}",
        f"- Specific teacher notes: {context.get('specifics') or 'none'}",
        "",
        "Analysis instruction:",
        "Use the UI target context as the teacher's intended use case. Extract what the document says, then check whether the lesson plan fits this UI context based on the actual tasks and activity load. If the document claims a different grade or age than the UI context, report the mismatch clearly.",
        "Subject focus instruction:",
        "Treat the selected subject(s) as the primary lens for feedback. If the document is stronger in other subjects than in the selected subject(s), say that clearly and suggest what would be needed to make it fit the selected subject(s).",
        f"Conduct the analysis strictly in the {language} language.",
    ]
    return "\n".join(lines)


def call_mistral_analysis(payload):
    if not config.MISTRAL_API_KEY:
        log_message("[mistral] Missing MISTRAL_API_KEY")
        return {
            "error": "MISTRAL_API_KEY is not configured in app/server/.env"
        }

    system_prompt = load_prompt_file("analysis_system_prompt.txt")

    context_summary = build_analysis_context_summary(payload)
    user_prompt = context_summary + "\n\nFull uploaded lesson payload:\n" + json.dumps(payload, ensure_ascii=False, indent=2)
    request_body = build_mistral_request_body(system_prompt, user_prompt)
    log_mistral_prompt("analysis", system_prompt, user_prompt, request_body)

    try:
        response_data = post_mistral_chat_completion(request_body, config.MISTRAL_ANALYSIS_TIMEOUT)
        log_message(f"[mistral] Response received, model={config.MISTRAL_MODEL}")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")
        log_message(f"[mistral] HTTPError {error.code}: {detail}")
        if error.code == 400 and "response_format" in detail:
            try:
                response_data = maybe_retry_without_response_format(request_body, config.MISTRAL_ANALYSIS_TIMEOUT, "mistral")
                log_message(f"[mistral] Response received after fallback, model={config.MISTRAL_MODEL}")
            except Exception as retry_error:
                log_message(f"[mistral] Fallback request failed: {retry_error}")
                log_message(traceback.format_exc())
                return {"error": f"Mistral request failed with HTTP {error.code}", "detail": detail}
        else:
            return {"error": f"Mistral request failed with HTTP {error.code}", "detail": detail}
    except Exception as error:
        log_message(f"[mistral] Request failed: {error}")
        log_message(traceback.format_exc())
        return {"error": f"Mistral request failed: {error}"}

    try:
        content = response_data["choices"][0]["message"]["content"]
        log_message(f"[mistral] Raw content preview: {content[:500]}")
        return parse_mistral_json_content(content, "mistral", config.MISTRAL_TEST_TIMEOUT)
    except Exception as error:
        log_message(f"[mistral] Could not parse response: {error}")
        log_message(traceback.format_exc())
        return {"error": f"Could not parse Mistral response as JSON: {error}", "raw": response_data}


def call_mistral_refinement(payload):
    if not config.MISTRAL_API_KEY:
        log_message("[mistral-step3] Missing MISTRAL_API_KEY")
        return {
            "error": "MISTRAL_API_KEY is not configured in app/server/.env"
        }

    system_prompt = load_prompt_file("refinement_system_prompt.txt")

    memory_summary = build_step3_memory_summary(payload)
    raw_payload = json.dumps(payload, ensure_ascii=False, indent=2)
    user_prompt = (
        memory_summary
        + "\n\n"
        + "=" * 72
        + "\nRaw current payload follows. Use it as source data, but prioritize the memory summary for dialogue continuity.\n"
        + "=" * 72
        + "\n"
        + raw_payload
    )
    request_body = build_mistral_request_body(system_prompt, user_prompt)
    log_mistral_prompt("refinement", system_prompt, user_prompt, request_body)

    try:
        response_data = post_mistral_chat_completion(request_body, config.MISTRAL_REFINEMENT_TIMEOUT)
        log_message(f"[mistral-step3] Response received, model={config.MISTRAL_MODEL}")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")
        log_message(f"[mistral-step3] HTTPError {error.code}: {detail}")
        if error.code == 400 and "response_format" in detail:
            try:
                response_data = maybe_retry_without_response_format(request_body, config.MISTRAL_REFINEMENT_TIMEOUT, "mistral-step3")
                log_message(f"[mistral-step3] Response received after fallback, model={config.MISTRAL_MODEL}")
            except Exception as retry_error:
                log_message(f"[mistral-step3] Fallback request failed: {retry_error}")
                log_message(traceback.format_exc())
                return {"error": f"Mistral refinement failed with HTTP {error.code}", "detail": detail}
        else:
            return {"error": f"Mistral refinement failed with HTTP {error.code}", "detail": detail}
    except Exception as error:
        log_message(f"[mistral-step3] Request failed: {error}")
        log_message(traceback.format_exc())
        return {"error": f"Mistral refinement failed: {error}"}

    try:
        content = response_data["choices"][0]["message"]["content"]
        log_message(f"[mistral-step3] Raw content preview: {content[:500]}")
        return parse_mistral_json_content(content, "mistral-step3", config.MISTRAL_TEST_TIMEOUT)
    except Exception as error:
        log_message(f"[mistral-step3] Could not parse response: {error}")
        log_message(traceback.format_exc())
        return {"error": f"Could not parse Mistral step 3 response as JSON: {error}", "raw": response_data}


def call_mistral_hello():
    if not config.MISTRAL_API_KEY:
        log_message("[mistral-test] Missing MISTRAL_API_KEY")
        return {"error": "MISTRAL_API_KEY is not configured in app/server/.env"}

    system_prompt = load_prompt_file("mistral_test_system_prompt.txt")
    request_body = {
        "model": config.MISTRAL_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Say hello."},
        ],
        "temperature": 0,
    }
    log_mistral_prompt("test", system_prompt, "Say hello.", request_body)

    request = urllib.request.Request(
        "https://api.mistral.ai/v1/chat/completions",
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.MISTRAL_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=config.MISTRAL_TEST_TIMEOUT) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")
        log_message(f"[mistral-test] HTTPError {error.code}: {detail}")
        return {"error": f"Mistral test failed with HTTP {error.code}", "detail": detail}
    except Exception as error:
        log_message(f"[mistral-test] Request failed: {error}")
        log_message(traceback.format_exc())
        return {"error": f"Mistral test failed: {error}"}

    try:
        content = response_data["choices"][0]["message"]["content"].strip().lower()
        log_message(f"[mistral-test] Raw content: {content}")
        if "hello" in content:
            return {"hello": "hello", "raw": content}
        return {"hello": content, "raw": content}
    except Exception as error:
        log_message(f"[mistral-test] Could not parse response: {error}")
        log_message(traceback.format_exc())
        return {"error": f"Could not parse Mistral test response: {error}", "raw": response_data}
