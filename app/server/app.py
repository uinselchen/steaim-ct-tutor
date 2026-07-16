import http.server
import os
import posixpath
import urllib.parse
import cgi
import json
import uuid
import webbrowser
import mimetypes
import tempfile
import urllib.request
import urllib.error
import traceback
import re
import unicodedata
import smtplib
from http import HTTPStatus
from email.message import EmailMessage

import config
from config import (
    AMENDMENTS_ROOT,
    APP_ROOT,
    CONFIG_FILE,
    CURRICULA_ROOT,
    DATA_ROOT,
    FRONTEND_ROOT,
    LESSONPLANS_ROOT,
    PORT,
    STEP3_STATE_ROOT,
)
import export_service
from export_service import normalize_filename_piece
from file_extractors import extract_text_from_file
from logging_utils import log_message, log_mistral_prompt
from prompts import load_prompt_file

def slugify_folder_name(value):
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "unknown"


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
            if isinstance(parsed, list):
                values = parsed
            else:
                values = [parsed]
        except Exception:
            values = [part.strip() for part in re.split(r"[;,]", text)]
    cleaned = []
    for item in values:
        item_text = str(item or "").strip()
        if item_text and item_text not in cleaned:
            cleaned.append(item_text)
    return cleaned


def ensure_step2_folder_structure(country, subjects):
    country_name = str(country or "").strip() or "unknown-country"
    country_slug = slugify_folder_name(country_name)
    created_paths = []

    curriculum_country_root = os.path.join(CURRICULA_ROOT, country_slug)
    amendments_country_root = os.path.join(AMENDMENTS_ROOT, country_slug)
    for root_path in (curriculum_country_root, amendments_country_root):
        os.makedirs(root_path, exist_ok=True)
        created_paths.append(root_path)

    normalized_subjects = parse_subjects_value(subjects)
    if not normalized_subjects:
        normalized_subjects = ["unknown-subject"]

    subject_paths = []
    for subject in normalized_subjects:
        subject_slug = slugify_folder_name(subject)
        curriculum_subject_path = os.path.join(curriculum_country_root, subject_slug)
        amendments_subject_path = os.path.join(amendments_country_root, subject_slug)
        os.makedirs(curriculum_subject_path, exist_ok=True)
        os.makedirs(amendments_subject_path, exist_ok=True)
        subject_paths.append(
            {
                "subject": subject,
                "slug": subject_slug,
                "curriculum": curriculum_subject_path,
                "amendments": amendments_subject_path,
            }
        )
        created_paths.extend([curriculum_subject_path, amendments_subject_path])

    return {
        "country": country_name,
        "countrySlug": country_slug,
        "curriculumRoot": curriculum_country_root,
        "amendmentsRoot": amendments_country_root,
        "subjects": subject_paths,
        "createdPaths": created_paths,
    }


def save_uploaded_files_to_folder(file_items, target_folder):
    saved_files = []
    os.makedirs(target_folder, exist_ok=True)

    for file_item in file_items:
        filename = os.path.basename(getattr(file_item, "filename", "") or "")
        if not filename:
            continue
        target_path = os.path.join(target_folder, filename)
        counter = 1
        base_name, extension = os.path.splitext(filename)
        while os.path.exists(target_path):
            target_path = os.path.join(target_folder, f"{base_name}-{counter}{extension}")
            counter += 1
        with open(target_path, "wb") as output_file:
            output_file.write(file_item.file.read())
        saved_files.append({
            "filename": os.path.basename(target_path),
            "path": target_path,
        })

    return saved_files


def step3_state_path(session_id):
    session = str(session_id or "").strip()
    if not session:
        return ""
    return os.path.join(STEP3_STATE_ROOT, f"{session}.json")


def step3_conversation_log_path(session_id):
    session = str(session_id or "").strip()
    if not session:
        return ""
    return os.path.join(STEP3_STATE_ROOT, f"{session}-conversation.txt")


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
        traceback.print_exc()
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
        traceback.print_exc()
        return None


def parse_bool_value(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def normalize_email_list(value):
    if not value:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = re.split(r"[;,]", str(value))
    cleaned = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


def build_draft_text(draft):
    draft = draft if isinstance(draft, dict) else {}
    lines = []
    lines.append(str(draft.get("title") or "Lesson Plan"))
    lines.append("")
    summary = str(draft.get("summary") or "").strip()
    if summary:
      lines.append("Summary")
      lines.append(summary)
      lines.append("")

    meta = draft.get("meta") if isinstance(draft.get("meta"), dict) else {}
    meta_lines = []
    for label, value in [
        ("Country", meta.get("country", "")),
        ("Subject(s)", ", ".join(meta.get("subjects", [])) if isinstance(meta.get("subjects"), list) else meta.get("subjects", "")),
        ("Grade range", meta.get("gradeRange", "")),
        ("Age range", meta.get("ageRange", "")),
        ("Focus", meta.get("focus", "")),
    ]:
        value_text = str(value or "").strip()
        if value_text:
            meta_lines.append(f"{label}: {value_text}")
    if meta_lines:
        lines.append("Meta")
        lines.extend(meta_lines)
        lines.append("")

    def add_list_section(title, items):
        items = items if isinstance(items, list) else []
        if not items:
            return
        lines.append(title)
        for item in items:
            lines.append(f"- {item}")
        lines.append("")

    add_list_section("Goals", draft.get("goals", []))
    add_list_section("Skills", draft.get("skills", []))

    steps = draft.get("steps", [])
    if isinstance(steps, list) and steps:
        lines.append("Steps")
        for index, step in enumerate(steps, start=1):
            step = step if isinstance(step, dict) else {}
            title = str(step.get("title", f"Step {index}")).strip()
            duration = str(step.get("duration", "")).strip()
            description = str(step.get("description", "")).strip()
            status = str(step.get("status", "")).strip()
            note = str(step.get("note", "")).strip()
            line = f"{index}. {title}" + (f" ({duration})" if duration else "")
            lines.append(line)
            if description:
                lines.append(f"   {description}")
            if status:
                lines.append(f"   Status: {status}")
            if note:
                lines.append(f"   Note: {note}")
        lines.append("")

    add_list_section("Materials", draft.get("materials", []))
    add_list_section("Assessment", draft.get("assessment", []))

    reflection = str(draft.get("reflection", "")).strip()
    if reflection:
        lines.append("Reflection")
        lines.append(reflection)
        lines.append("")

    changes = draft.get("changes", [])
    if isinstance(changes, list) and changes:
        lines.append("Change summary")
        for change in changes:
            change = change if isinstance(change, dict) else {}
            title = str(change.get("title", "Change")).strip()
            reason = str(change.get("reason", "")).strip()
            source = str(change.get("source", "")).strip()
            heading = title + (f" - {source}" if source else "")
            lines.append(heading)
            if reason:
                lines.append(reason)
        lines.append("")

    return "\n".join(lines).strip()


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

        memory_summary = build_step3_memory_summary(payload, conversation, draft)
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
        traceback.print_exc()
        return False


def send_summary_email(payload):
    if not config.SMTP_HOST:
        return {"error": "SMTP_HOST is not configured in app/server/.env"}

    recipient = config.MAIL_TO_ADDRESS or str(payload.get("recipient", "")).strip()
    if not recipient:
        return {"error": "MAIL_TO_ADDRESS is not configured in app/server/.env"}

    recipients = normalize_email_list(recipient)
    if not recipients:
        return {"error": "No valid email recipient configured"}

    context = export_service.build_export_context(payload, load_step3_state)
    draft = context.get("draft") if isinstance(context.get("draft"), dict) else {}
    conversation = context.get("conversation") if isinstance(context.get("conversation"), list) else []
    session_id = str(context.get("sessionId", "")).strip()

    message = EmailMessage()
    message["Subject"] = f"STEaiM-CT lesson plan{f' ({session_id})' if session_id else ''}"
    message["From"] = config.MAIL_FROM_ADDRESS or config.SMTP_USERNAME or recipients[0]
    message["To"] = ", ".join(recipients)

    draft_text = build_draft_text(draft)
    conversation_text = build_conversation_text(conversation)

    body_lines = [
        "Here is the final lesson plan and the conversation from the local tutor.",
        "",
        "Lesson plan preview:",
        draft_text or "(no draft available)",
        "",
        "Conversation preview:",
        conversation_text or "(no conversation available)",
    ]
    message.set_content("\n".join(body_lines))

    try:
        bundle = export_service.build_export_bundle(context)
    except Exception:
        log_message("[mail] Export bundle could not be generated, sending text only")
        traceback.print_exc()
        bundle = None

    if conversation_text:
        message.add_attachment(conversation_text.encode("utf-8"), maintype="text", subtype="plain", filename="conversation.txt")
    if bundle and os.path.exists(bundle.get("pdfPath", "")):
        with open(bundle["pdfPath"], "rb") as pdf_file:
            pdf_bytes = pdf_file.read()
        message.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=os.path.basename(bundle["pdfPath"]))
    elif draft_text:
        message.add_attachment(draft_text.encode("utf-8"), maintype="text", subtype="plain", filename="lesson-plan-draft.txt")

    try:
        if config.SMTP_USE_SSL:
            with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as smtp:
                if config.SMTP_USERNAME:
                    smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD or "")
                smtp.send_message(message)
        else:
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as smtp:
                if config.SMTP_USE_TLS:
                    smtp.starttls()
                if config.SMTP_USERNAME:
                    smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD or "")
                smtp.send_message(message)
    except Exception as error:
        log_message(f"[mail] Send failed: {error}")
        traceback.print_exc()
        return {"error": f"Unable to send email: {error}"}

    return {
        "sent": True,
        "recipient": recipients,
        "subject": message["Subject"],
    }


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
        "https://api.mistral.ai/v1/chat/completions",
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
        traceback.print_exc()
        return {"error": f"Could not parse Mistral test response: {error}", "raw": response_data}


config.load_env_file()

if not os.path.exists(CONFIG_FILE):
    default_config = {
        "countries": [
            "Slovakia",
            "Germany",
            "Austria",
            "Spain",
            "Czech Republic",
            "Poland",
            "Portugal",
            "Italy"
        ],
        "subjects": [
            "Mathematics",
            "Informatics / CS",
            "Biology",
            "Physics",
            "Chemistry"
        ]
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as config_file:
        json.dump(default_config, config_file, indent=2)

class TutorHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        route = urllib.parse.urlparse(self.path).path

        if route in ("", "/"):
            self.serve_file(os.path.join(FRONTEND_ROOT, "start.html"), "text/html")
        elif route == "/ping":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
        elif route == "/step3-state":
            self.handle_step3_state()
        elif route == "/config":
            self.serve_config()
        elif route.startswith("/data/curricula/"):
            self.serve_path(route[len("/data/curricula/"):], CURRICULA_ROOT)
        elif route.startswith("/frontend/"):
            self.serve_path(route[len("/frontend/"):], FRONTEND_ROOT)
        else:
            self.serve_path(route.lstrip("/"), FRONTEND_ROOT)

    def do_POST(self):
        route = urllib.parse.urlparse(self.path).path
        if route == "/upload":
            self.handle_upload()
        elif route == "/analyze":
            self.handle_analyze()
        elif route == "/step2-prepare":
            self.handle_step2_prepare()
        elif route == "/step3-refine":
            self.handle_step3_refine()
        elif route == "/send-email":
            self.handle_send_email()
        elif route == "/export-docx":
            self.handle_export_docx()
        elif route == "/export-pdf":
            self.handle_export_pdf()
        elif route == "/mistral-test":
            self.handle_mistral_test()
        elif route == "/client-log":
            self.handle_client_log()
        elif route == "/config":
            self.handle_config_update()
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def handle_upload(self):
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            self.send_error(HTTPStatus.BAD_REQUEST, "Expected multipart/form-data")
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
            },
        )

        if "lessonPlan" not in form and "file" not in form:
            self.send_error(HTTPStatus.BAD_REQUEST, "No file field provided")
            return

        file_item = form["lessonPlan"] if "lessonPlan" in form else form["file"]
        filename = os.path.basename(file_item.filename or "")

        if not filename:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid filename")
            return

        target_path = os.path.join(LESSONPLANS_ROOT, filename)
        try:
            with open(target_path, "wb") as output_file:
                output_file.write(file_item.file.read())
        except OSError:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Unable to save file")
            return

        specifics = form.getvalue("specifics", "").strip()
        specifics_filename = None
        if specifics:
            specifics_filename = f"specifics-{uuid.uuid4().hex[:8]}.txt"
            specifics_path = os.path.join(DATA_ROOT, "outputs", specifics_filename)
            try:
                with open(specifics_path, "w", encoding="utf-8") as specifics_file:
                    specifics_file.write(specifics)
            except OSError:
                self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Unable to save specifics")
                return

        response_body = {"saved": filename}
        if specifics_filename:
            response_body["specificsSaved"] = specifics_filename

        self.send_response(HTTPStatus.CREATED)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response_body).encode("utf-8"))

    def handle_analyze(self):
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            self.send_error(HTTPStatus.BAD_REQUEST, "Expected multipart/form-data")
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
            },
        )

        if "lessonPlan" not in form and "file" not in form:
            self.send_error(HTTPStatus.BAD_REQUEST, "No file field provided")
            return

        file_item = form["lessonPlan"] if "lessonPlan" in form else form["file"]
        filename = os.path.basename(file_item.filename or "")
        if not filename:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid filename")
            return

        log_message(f"[analyze] Received file={filename}")

        temp_suffix = os.path.splitext(filename)[1] or ".bin"
        file_bytes = file_item.file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=temp_suffix) as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        try:
            extracted_text = extract_text_from_file(temp_path)
        finally:
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

        lessonplan_upload_root = os.path.join(LESSONPLANS_ROOT, "uploads")
        os.makedirs(lessonplan_upload_root, exist_ok=True)
        stored_filename = f"{uuid.uuid4().hex[:12]}-{normalize_filename_piece(os.path.splitext(filename)[0])}{temp_suffix.lower()}"
        stored_path = os.path.join(lessonplan_upload_root, stored_filename)
        try:
            with open(stored_path, "wb") as output_file:
                output_file.write(file_bytes)
        except OSError:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Unable to save uploaded lesson plan")
            return

        log_message(f"[analyze] Extracted chars={len(extracted_text)}")

        specifics = form.getvalue("specifics", "").strip()
        subjects_value = []
        if "subjects[]" in form:
            subjects_field = form["subjects[]"]
            if isinstance(subjects_field, list):
                subjects_value = [item.value for item in subjects_field]
            else:
                subjects_value = [subjects_field.value]
        elif "subjects" in form:
            subjects_value = parse_subjects_value(form.getvalue("subjects", ""))
        subject_other = form.getvalue("subjectOther", "").strip()
        if subject_other:
            subjects_value.append(subject_other)
        subjects_value = parse_subjects_value(subjects_value)
        metadata = {
            "filename": filename,
            "country": form.getvalue("country", "").strip(),
            "subjects": subjects_value,
            "gradeFrom": form.getvalue("gradeFrom", "").strip(),
            "gradeTo": form.getvalue("gradeTo", "").strip(),
            "ageFrom": form.getvalue("ageFrom", "").strip(),
            "ageTo": form.getvalue("ageTo", "").strip(),
            "specifics": specifics,
            "documentText": extracted_text[:30000],
            "sourceDocument": {
                "filename": filename,
                "storedFilename": stored_filename,
                "path": stored_path,
            },
        }

        log_message(
            "[analyze] Meta country={country} subjects={subjects} grade={g1}-{g2} age={a1}-{a2}".format(
                country=metadata["country"],
                subjects=", ".join(metadata["subjects"]),
                g1=metadata["gradeFrom"],
                g2=metadata["gradeTo"],
                a1=metadata["ageFrom"],
                a2=metadata["ageTo"],
            )
        )
        if not extracted_text.strip():
            log_message("[analyze] Warning: extracted text is empty")
            if temp_suffix.lower() == ".pdf":
                analysis = {
                    "error": "Could not extract readable text from this PDF. If it is scanned or image-based, please upload a DOCX/TXT version or a PDF with selectable text.",
                    "sourceDocument": metadata["sourceDocument"],
                }
                self.send_response(HTTPStatus.UNPROCESSABLE_ENTITY)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(analysis).encode("utf-8"))
                return

        analysis_request_metadata = dict(metadata)
        analysis_request_metadata.pop("sourceDocument", None)
        analysis_request_metadata["ui_target_context"] = build_ui_target_context(metadata)
        analysis = call_mistral_analysis(analysis_request_metadata)
        if isinstance(analysis, dict):
            analysis["sourceDocument"] = metadata["sourceDocument"]
        if "error" in analysis:
            log_message(f"[analyze] Failed: {analysis.get('error')}")
            self.send_response(HTTPStatus.BAD_GATEWAY)
        else:
            log_message("[analyze] Success")
            self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(analysis, ensure_ascii=False).encode("utf-8"))

    def handle_step2_prepare(self):
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("multipart/form-data"):
            self.send_error(HTTPStatus.BAD_REQUEST, "Expected multipart/form-data")
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
            },
        )

        country = form.getvalue("country", "").strip()
        if not country:
            self.send_error(HTTPStatus.BAD_REQUEST, "Missing country")
            return

        subjects_value = []
        if "subjects[]" in form:
            subjects_field = form["subjects[]"]
            if isinstance(subjects_field, list):
                subjects_value = [item.value for item in subjects_field]
            else:
                subjects_value = [subjects_field.value]
        elif "subjects" in form:
            subjects_field = form["subjects"]
            if isinstance(subjects_field, list):
                subjects_value = [item.value for item in subjects_field]
            else:
                subjects_value = [subjects_field.value]
        else:
            parsed_subjects = parse_subjects_value(form.getvalue("subjects", ""))
            subjects_value = parsed_subjects

        folder_info = ensure_step2_folder_structure(country, subjects_value)
        session_id = uuid.uuid4().hex[:12]
        session_root = os.path.join(folder_info["amendmentsRoot"], f"step2-{session_id}")
        os.makedirs(session_root, exist_ok=True)

        source_document = None
        raw_source_document = form.getvalue("sourceDocument", "")
        if raw_source_document:
            try:
                source_document = export_service.normalize_source_document(json.loads(raw_source_document))
            except Exception:
                source_document = export_service.normalize_source_document(raw_source_document)

        saved_files = []
        if "additionalFiles" in form:
            additional_field = form["additionalFiles"]
            file_items = additional_field if isinstance(additional_field, list) else [additional_field]
            saved_files = save_uploaded_files_to_folder(file_items, session_root)

        metadata_path = os.path.join(session_root, "step2-metadata.json")
        metadata = {
            "country": folder_info["country"],
            "subjects": [item["subject"] for item in folder_info["subjects"]],
            "sessionId": session_id,
            "createdPaths": folder_info["createdPaths"],
            "savedFiles": saved_files,
            "gradeFrom": form.getvalue("gradeFrom", "").strip(),
            "gradeTo": form.getvalue("gradeTo", "").strip(),
            "ageFrom": form.getvalue("ageFrom", "").strip(),
            "ageTo": form.getvalue("ageTo", "").strip(),
            "specifics": form.getvalue("specifics", "").strip(),
            "selections": form.getvalue("selections", "").strip(),
            "filename": form.getvalue("filename", "").strip(),
            "sourceDocument": source_document,
        }
        try:
            with open(metadata_path, "w", encoding="utf-8") as metadata_file:
                json.dump(metadata, metadata_file, ensure_ascii=False, indent=2)
        except OSError:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Unable to save step 2 metadata")
            return

        log_message(
            "[step2] Prepared country={country} subjects={subjects} files={count}".format(
                country=folder_info["country"],
                subjects=", ".join(item["subject"] for item in folder_info["subjects"]),
                count=len(saved_files),
            )
        )

        response_body = {
            "prepared": True,
            "sessionId": session_id,
            "country": folder_info["country"],
            "countrySlug": folder_info["countrySlug"],
            "subjects": folder_info["subjects"],
            "amendmentsRoot": folder_info["amendmentsRoot"],
            "curriculumRoot": folder_info["curriculumRoot"],
            "savedFiles": saved_files,
            "filename": metadata["filename"],
            "sourceDocument": source_document,
        }

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response_body, ensure_ascii=False).encode("utf-8"))

    def handle_export_docx(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))
        except Exception:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON")
            return

        try:
            context = export_service.build_export_context(data, load_step3_state)
            bundle = export_service.build_export_bundle(context)
            export_path = bundle["docxPath"]
            with open(export_path, "rb") as export_file:
                docx_bytes = export_file.read()
        except Exception:
            log_message("[export] DOCX generation failed")
            log_message(traceback.format_exc())
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Unable to generate DOCX")
            return

        export_name = os.path.basename(export_path)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        self.send_header("Content-Disposition", f'attachment; filename="{export_name}"')
        self.send_header("Content-Length", str(len(docx_bytes)))
        self.end_headers()
        self.wfile.write(docx_bytes)

    def handle_export_pdf(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))
        except Exception:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON")
            return

        try:
            context = export_service.build_export_context(data, load_step3_state)
            bundle = export_service.build_export_bundle(context)
            export_path = bundle["pdfPath"]
            with open(export_path, "rb") as export_file:
                pdf_bytes = export_file.read()
        except Exception:
            log_message("[export] PDF generation failed")
            log_message(traceback.format_exc())
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Unable to generate PDF")
            return

        export_name = os.path.basename(export_path)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Disposition", f'attachment; filename="{export_name}"')
        self.send_header("Content-Length", str(len(pdf_bytes)))
        self.end_headers()
        self.wfile.write(pdf_bytes)

    def handle_step3_refine(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON")
            return

        if not isinstance(payload, dict):
            self.send_error(HTTPStatus.BAD_REQUEST, "Missing payload")
            return

        focus_id = ""
        current_node = payload.get("currentNode")
        if isinstance(current_node, dict):
            focus_id = str(current_node.get("id", "")).strip()

        session_id = str(payload.get("sessionId", "")).strip()
        log_message(f"[mistral-step3] Refinement request session={session_id or 'unknown'} focus={focus_id or 'unknown'}")

        result = call_mistral_refinement(payload)
        session_id = str(payload.get("sessionId", "")).strip()
        if session_id:
            saved_conversation = list(payload.get("conversation", [])) if isinstance(payload.get("conversation", []), list) else []
            assistant_message = str(result.get("assistant_message", "")).strip() if isinstance(result, dict) else ""
            if assistant_message:
                saved_conversation.append({
                    "role": "tutor",
                    "text": assistant_message,
                    "time": payload.get("timestamp", ""),
                    "extraClass": ""
                })
            state_snapshot = {
                "sessionId": session_id,
                "draft": result.get("updated_draft") if isinstance(result, dict) and isinstance(result.get("updated_draft"), dict) else payload.get("draft"),
                "conversation": saved_conversation,
                "progress": payload.get("progress") if isinstance(payload.get("progress"), dict) else {},
                "currentNodeId": payload.get("currentNode", {}).get("id") if isinstance(payload.get("currentNode"), dict) else "",
                "sourceDocument": payload.get("sourceDocument") if isinstance(payload.get("sourceDocument"), dict) else None,
                "payload": payload,
                "result": result,
            }
            save_step3_state(session_id, state_snapshot)
            save_step3_conversation_log(session_id, saved_conversation, payload, result)
        if "error" in result:
            log_message(f"[mistral-step3] Failed: {result.get('error')}")
            self.send_response(HTTPStatus.BAD_GATEWAY)
        else:
            log_message("[mistral-step3] Success")
            self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))

    def handle_step3_state(self):
        session_id = ""
        try:
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            session_id = str(params.get("sessionId", [""])[0]).strip()
        except Exception:
            session_id = ""

        if not session_id:
            self.send_error(HTTPStatus.BAD_REQUEST, "Missing sessionId")
            return

        state = load_step3_state(session_id)
        if not state:
            self.send_error(HTTPStatus.NOT_FOUND, "Step 3 state not found")
            return

        body = json.dumps(state, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_send_email(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON")
            return

        if not isinstance(payload, dict):
            self.send_error(HTTPStatus.BAD_REQUEST, "Missing payload")
            return

        result = send_summary_email(payload)
        if "error" in result:
            log_message(f"[mail] Failed: {result.get('error')}")
            self.send_response(HTTPStatus.BAD_GATEWAY)
        else:
            log_message(f"[mail] Sent to {', '.join(result.get('recipient', []))}")
            self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))

    def handle_mistral_test(self):
        log_message("[mistral-test] Starting hello check")
        result = call_mistral_hello()
        if "error" in result:
            log_message(f"[mistral-test] Failed: {result.get('error')}")
            self.send_response(HTTPStatus.BAD_GATEWAY)
        else:
            log_message("[mistral-test] Success")
            self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))

    def handle_client_log(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))
        except Exception:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON")
            return

        message = ""
        if isinstance(data, dict):
            message = str(data.get("message", "")).strip()

        if not message:
            self.send_error(HTTPStatus.BAD_REQUEST, "Missing message")
            return

        log_message(f"[client] {message}")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"saved": True}).encode("utf-8"))

    def serve_config(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "Config file not found")

    def handle_config_update(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))
        except Exception:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON")
            return

        if not isinstance(data, dict) or ("newSubject" not in data and "newCountry" not in data):
            self.send_error(HTTPStatus.BAD_REQUEST, "Missing newSubject or newCountry")
            return

        new_subject = None
        new_country = None
        if "newSubject" in data:
            new_subject = str(data["newSubject"]).strip()
        if "newCountry" in data:
            new_country = str(data["newCountry"]).strip()

        if new_subject is not None and not new_subject:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid subject")
            return
        if new_country is not None and not new_country:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid country")
            return

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            config = {"countries": [], "subjects": []}

        saved_item = None
        if new_subject is not None:
            if new_subject not in config.get("subjects", []):
                config.setdefault("subjects", []).append(new_subject)
                saved_item = new_subject
        if new_country is not None:
            if new_country not in config.get("countries", []):
                config.setdefault("countries", []).append(new_country)
                saved_item = new_country

        if saved_item is not None:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"saved": saved_item}).encode("utf-8"))

    def serve_path(self, rel_path, root):
        rel_path = rel_path.lstrip("/")
        safe_path = posixpath.normpath(urllib.parse.unquote(rel_path))
        if safe_path.startswith(".."):
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return

        file_path = os.path.join(root, safe_path)
        if os.path.isdir(file_path):
            self.send_error(HTTPStatus.FORBIDDEN, "Directory listing is not allowed")
            return
        if not os.path.exists(file_path):
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        self.serve_file(file_path, self.guess_type(file_path))

    def serve_file(self, file_path, content_type):
        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")

    def guess_type(self, path):
        if path.endswith(".html"):
            return "text/html"
        if path.endswith(".css"):
            return "text/css"
        if path.endswith(".js"):
            return "application/javascript"
        if path.endswith(".json"):
            return "application/json"
        if path.endswith(".png"):
            return "image/png"
        if path.endswith(".jpg") or path.endswith(".jpeg"):
            return "image/jpeg"
        if path.endswith(".svg"):
            return "image/svg+xml"
        if path.endswith(".pdf"):
            return "application/pdf"
        return "application/octet-stream"

def run_server():
    os.chdir(APP_ROOT)
    server_address = ("", PORT)
    httpd = http.server.HTTPServer(server_address, TutorHandler)
    url = f"http://localhost:{PORT}"
    webbrowser.open(url)
    log_message(f"Starting server at {url}")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()

