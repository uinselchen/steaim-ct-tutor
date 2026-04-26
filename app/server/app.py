import http.server
import os
import posixpath
import urllib.parse
import cgi
import json
import uuid
import webbrowser
from http import HTTPStatus

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, ".."))
FRONTEND_ROOT = os.path.join(APP_ROOT, "frontend")
DATA_ROOT = os.path.join(APP_ROOT, "data")
CURRICULA_ROOT = os.path.join(DATA_ROOT, "curricula")
LESSONPLANS_ROOT = os.path.join(DATA_ROOT, "lessonplans")
CONFIG_FILE = os.path.join(DATA_ROOT, "config.json")

PORT = 8000

for path in (
    FRONTEND_ROOT,
    CURRICULA_ROOT,
    LESSONPLANS_ROOT,
    os.path.join(DATA_ROOT, "templates"),
    os.path.join(DATA_ROOT, "outputs"),
):
    os.makedirs(path, exist_ok=True)

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
    print(f"Starting server at {url}")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
