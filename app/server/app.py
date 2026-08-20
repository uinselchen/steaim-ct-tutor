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
import traceback
from http import HTTPStatus

import config
import email_service
import mistral_service
import settings_service
import step2_service
import step3_service
from config import (
    APP_ROOT,
    CONFIG_FILE,
    CURRICULA_ROOT,
    DATA_ROOT,
    FRONTEND_ROOT,
    LESSONPLANS_ROOT,
    PORT,
)
import export_service
from export_service import normalize_filename_piece
from file_extractors import extract_text_from_file
from logging_utils import log_message
from text_utils import parse_subjects_value

def parse_bool_value(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


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
        elif route == "/settings-status":
            self.serve_settings_status()
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
        elif route == "/settings":
            self.handle_settings_update()
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
        analysis_request_metadata["ui_target_context"] = mistral_service.build_ui_target_context(metadata)
        analysis = mistral_service.call_mistral_analysis(analysis_request_metadata)
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

        folder_info = step2_service.ensure_step2_folder_structure(country, subjects_value)
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
            saved_files = step2_service.save_uploaded_files_to_folder(file_items, session_root)

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
            context = export_service.build_export_context(data, step3_service.load_step3_state)
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
            context = export_service.build_export_context(data, step3_service.load_step3_state)
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

        result = mistral_service.call_mistral_refinement(payload)
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
            step3_service.save_step3_state(session_id, state_snapshot)
            step3_service.save_step3_conversation_log(session_id, saved_conversation, payload, result)
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

        state = step3_service.load_step3_state(session_id)
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

        result = email_service.send_summary_email(payload, step3_service.load_step3_state)
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
        result = mistral_service.call_mistral_hello()
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

    def serve_settings_status(self):
        status = settings_service.build_settings_status()
        content = json.dumps(status, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def handle_settings_update(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))
        except Exception:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid JSON")
            return

        result = settings_service.update_mistral_settings(data)
        if "error" in result:
            self.send_response(HTTPStatus.BAD_REQUEST)
        else:
            log_message(f"[settings] Updated {', '.join(result.get('updated', []))}")
            self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))

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

