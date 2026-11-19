import threading
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


def pytest_addoption(parser):
    parser.addoption("--run-browser", action="store_true", help="Run Chromium integration tests")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-browser"):
        skip = pytest.mark.skip(reason="use --run-browser after installing Chromium")
        for item in items:
            if "browser" in item.keywords:
                item.add_marker(skip)


@pytest.fixture
def web_server():
    routes = {"/robots.txt": (200, {"Content-Type": "text/plain"}, b"User-agent: *\nAllow: /\n")}
    hits = Counter()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            hits[self.path] += 1
            response = routes.get(self.path, (404, {"Content-Type": "text/plain"}, b"Not found"))
            status, headers, body = response(hits[self.path]) if callable(response) else response
            if isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(status)
            for name, value in headers.items():
                if value is not None:
                    self.send_header(name, value)
            if "Content-Length" not in headers:
                self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()

    class Site:
        base = f"http://127.0.0.1:{server.server_port}"

        def add(
            self, path, body="", status=200, content_type="text/html; charset=utf-8", **headers
        ):
            routes[path] = (status, {"Content-Type": content_type, **headers}, body)

    site = Site()
    site.hits = hits
    site.routes = routes
    try:
        yield site
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
