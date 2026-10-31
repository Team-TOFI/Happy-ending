"""Disposable demo UI and same-origin proxy; independent of frontend/ and backend/."""

import argparse
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/recommendations":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400)
            return
        if not 0 < length <= 65536:
            self.send_error(413)
            return
        payload = self.rfile.read(length)
        request = Request(
            self.server.backend + "/recommendations",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlopen(request, timeout=180) as response:
                self.json_response(response.status, response.read())
        except HTTPError as error:
            self.json_response(error.code, error.read())
        except (URLError, TimeoutError, OSError):
            self.json_response(
                502,
                json.dumps(
                    {
                        "detail": "추천 서버에 연결할 수 없습니다. 백엔드 실행 상태를 확인해 주세요."
                    },
                    ensure_ascii=False,
                ).encode(),
            )

    def json_response(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=3001)
    parser.add_argument("--backend", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port), partial(Handler, directory=str(ROOT / "public"))
    )
    server.backend = args.backend.rstrip("/")
    print(f"Demo: http://localhost:{args.port} → {server.backend}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
