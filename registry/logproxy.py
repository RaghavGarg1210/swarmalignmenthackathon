"""Logging reverse proxy in front of pypiserver.

Every request an agent sandbox makes to the shared package index passes
through here. We log one JSON line per request (client IP, method, path,
status, sizes, user agent, uploaded filenames) and keep a copy of every
request body that is not a GET/HEAD, so uploads can be analysed later.

Standard library only, so it runs in any python image.
"""

import http.client
import json
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LISTEN_PORT = int(os.environ.get("PROXY_PORT", "8080"))
BACKEND_HOST = os.environ.get("BACKEND_HOST", "pypiserver")
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8081"))
LOG_DIR = os.environ.get("LOG_DIR", "/logs")
MAX_BODY_SAVE = int(os.environ.get("MAX_BODY_SAVE", str(50 * 1024 * 1024)))

HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}
FILENAME_RE = re.compile(rb'filename="([^"]{1,300})"')

_log_lock = threading.Lock()
os.makedirs(os.path.join(LOG_DIR, "bodies"), exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "requests.jsonl")


def _write_log(record: dict) -> None:
    line = json.dumps(record, ensure_ascii=False)
    with _log_lock:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    server_version = "nginx"  # look like an ordinary web front end
    sys_version = ""

    def log_message(self, format, *args):  # silence default stderr logging
        pass

    def _read_body(self) -> bytes:
        te = (self.headers.get("Transfer-Encoding") or "").lower()
        if "chunked" in te:
            chunks = []
            while True:
                size_line = self.rfile.readline().strip()
                size = int(size_line.split(b";")[0] or b"0", 16)
                if size == 0:
                    # consume trailer
                    while self.rfile.readline().strip():
                        pass
                    break
                chunks.append(self.rfile.read(size))
                self.rfile.readline()
            return b"".join(chunks)
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length) if length > 0 else b""

    def _handle(self) -> None:
        t0 = time.time()
        req_id = uuid.uuid4().hex[:12]
        body = self._read_body() if self.command not in ("GET", "HEAD") else b""
        record = {
            "id": req_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "epoch": t0,
            "client_ip": self.client_address[0],
            "method": self.command,
            "path": self.path,
            "user_agent": self.headers.get("User-Agent", ""),
            "req_bytes": len(body),
        }
        if body:
            record["upload_filenames"] = [
                m.decode("utf-8", "replace") for m in FILENAME_RE.findall(body[:2_000_000])
            ]
            if len(body) <= MAX_BODY_SAVE:
                body_path = os.path.join(LOG_DIR, "bodies", f"{int(t0)}_{req_id}.bin")
                with open(body_path, "wb") as f:
                    f.write(body)
                record["body_file"] = os.path.basename(body_path)

        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP_BY_HOP}
        headers["X-Forwarded-For"] = self.client_address[0]
        if body:
            headers["Content-Length"] = str(len(body))
        try:
            conn = http.client.HTTPConnection(BACKEND_HOST, BACKEND_PORT, timeout=120)
            conn.request(self.command, self.path, body=body or None, headers=headers)
            resp = conn.getresponse()
            resp_body = resp.read()
            self.send_response(resp.status, resp.reason)
            for k, v in resp.getheaders():
                if k.lower() in HOP_BY_HOP or k.lower() in ("content-length", "server", "date"):
                    continue
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(resp_body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(resp_body)
            record["status"] = resp.status
            record["resp_bytes"] = len(resp_body)
            conn.close()
        except Exception as e:  # backend down or client hung up
            record["status"] = 502
            record["error"] = repr(e)
            try:
                self.send_error(502)
            except Exception:
                pass
        record["ms"] = round((time.time() - t0) * 1000, 1)
        _write_log(record)

    do_GET = do_HEAD = do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _handle


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", LISTEN_PORT), Handler)
    server.daemon_threads = True
    print(f"logproxy :{LISTEN_PORT} -> {BACKEND_HOST}:{BACKEND_PORT}, logging to {LOG_PATH}", flush=True)
    server.serve_forever()
