import http.server
import os
import posixpath
import urllib.parse
import cgi
import json
import webbrowser
from http import HTTPStatus

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.abspath(os.path.join(HERE, ".."))
FRONTEND_ROOT = os.path.join(APP_ROOT, "frontend")
DATA_ROOT = os.path.join(APP_ROOT, "data")
CURRICULA_ROOT = os.path.join(DATA_ROOT, "curricula")
LESSONPLANS_ROOT = os.path.join(DATA_ROOT, "lessonplans")

PORT = 8000

for path in (
    FRONTEND_ROOT,
    CURRICULA_ROOT,
    LESSONPLANS_ROOT,
    os.path.join(DATA_ROOT, "templates"),
    os.path.join(DATA_ROOT, "outputs"),
):
    os.makedirs(path, exist_ok=True)

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

        if "file" not in form:
            self.send_error(HTTPStatus.BAD_REQUEST, "No file field provided")
            return

        file_item = form["file"]
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

        self.send_response(HTTPStatus.CREATED)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"saved": filename}).encode("utf-8"))

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
