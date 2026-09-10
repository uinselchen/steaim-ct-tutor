import re
import smtplib
import traceback
from email.message import EmailMessage

import config
import export_service
from logging_utils import log_message
from text_utils import build_conversation_text


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


def build_change_steps_text(context):
    context = context if isinstance(context, dict) else {}
    draft = context.get("draft") if isinstance(context.get("draft"), dict) else {}
    changes = export_service.collect_export_changes(context)
    lines = []
    lines.append("STEaiM-CT Tutor change steps")
    lines.append("")

    session_id = str(context.get("sessionId", "")).strip()
    if session_id:
        lines.append(f"Session: {session_id}")

    source_document = context.get("sourceDocument") if isinstance(context.get("sourceDocument"), dict) else {}
    filename = str(source_document.get("filename", "")).strip()
    if filename:
        lines.append(f"Uploaded file: {filename}")

    meta = draft.get("meta") if isinstance(draft.get("meta"), dict) else {}
    meta_lines = []
    for label, value in [
        ("Country", meta.get("country", "")),
        ("Subject(s)", ", ".join(meta.get("subjects", [])) if isinstance(meta.get("subjects"), list) else meta.get("subjects", "")),
        ("Grade range", meta.get("gradeRange", "")),
        ("Age range", meta.get("ageRange", "")),
    ]:
        value_text = str(value or "").strip()
        if value_text:
            meta_lines.append(f"{label}: {value_text}")
    if meta_lines:
        lines.extend(meta_lines)
    if session_id or filename or meta_lines:
        lines.append("")

    summary = str(draft.get("summary") or "").strip()
    if summary:
        lines.append("Lesson plan summary:")
        lines.append(summary)
        lines.append("")

    lines.append("Change steps:")
    if not changes:
        lines.append("(no changes recorded)")
    for index, change in enumerate(changes, start=1):
        title = str(change.get("title") or "Change").strip()
        location = str(change.get("location") or "").strip()
        reason = str(change.get("reason") or "").strip()
        before_value = str(change.get("beforeValue") or "").strip()
        after_value = str(change.get("afterValue") or "").strip()

        heading = f"{index}. {title}"
        if location:
            heading += f" @ {location}"
        lines.append(heading)
        if reason:
            lines.append(f"   Reason: {reason}")
        if before_value or after_value:
            lines.append(f"   Before: {before_value or '(not recorded)'}")
            lines.append(f"   After: {after_value or '(not recorded)'}")
        lines.append("")

    return "\n".join(lines).strip()


def build_analysis_points_text(context, field, heading):
    context = context if isinstance(context, dict) else {}
    payload = context.get("payload") if isinstance(context.get("payload"), dict) else {}
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    points = analysis.get(field) if isinstance(analysis.get(field), list) else []
    lines = [f"STEaiM-CT Tutor {heading.lower()}", ""]
    if not points:
        lines.append(f"(no {heading.lower()} recorded)")
        return "\n".join(lines)

    for index, point in enumerate(points, start=1):
        if isinstance(point, dict):
            title = str(point.get("title") or point.get("point") or "Point").strip()
            explanation = str(
                point.get("short_explanation")
                or point.get("description")
                or point.get("why_it_matters")
                or point.get("text")
                or ""
            ).strip()
        else:
            title = str(point).strip()
            explanation = ""
        lines.append(f"{index}. {title}")
        if explanation and explanation != title:
            lines.append(f"   {explanation}")
        lines.append("")
    return "\n".join(lines).strip()


def send_summary_email(payload, state_loader=None):
    if not config.SMTP_HOST:
        return {"error": "SMTP_HOST is not configured in app/server/.env"}

    recipient = config.MAIL_TO_ADDRESS or str(payload.get("recipient", "")).strip()
    if not recipient:
        return {"error": "MAIL_TO_ADDRESS is not configured in app/server/.env"}

    recipients = normalize_email_list(recipient)
    if not recipients:
        return {"error": "No valid email recipient configured"}

    context = export_service.build_export_context(payload, state_loader)
    session_id = str(context.get("sessionId", "")).strip()

    message = EmailMessage()
    message["Subject"] = f"STEaiM-CT tutor change log{f' ({session_id})' if session_id else ''}"
    message["From"] = config.MAIL_FROM_ADDRESS or config.SMTP_USERNAME or recipients[0]
    message["To"] = ", ".join(recipients)

    change_steps_text = build_change_steps_text(context)
    pros_text = build_analysis_points_text(context, "strengths", "Pros")
    cons_text = build_analysis_points_text(context, "issues", "Cons")

    body_lines = [
        "Here are the tutor change steps, pros, and cons.",
        "",
        "Attached files:",
        "- change-steps.txt",
        "- pros.txt",
        "- cons.txt",
        "",
        "This email intentionally does not include the lesson plan export or conversation log.",
    ]
    message.set_content("\n".join(body_lines))

    message.add_attachment(change_steps_text.encode("utf-8"), maintype="text", subtype="plain", filename="change-steps.txt")
    message.add_attachment(pros_text.encode("utf-8"), maintype="text", subtype="plain", filename="pros.txt")
    message.add_attachment(cons_text.encode("utf-8"), maintype="text", subtype="plain", filename="cons.txt")

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
        log_message(traceback.format_exc())
        return {"error": f"Unable to send email: {error}"}

    return {
        "sent": True,
        "recipient": recipients,
        "subject": message["Subject"],
    }
