from __future__ import annotations

import os

import requests
from dotenv import load_dotenv
from flask import Flask, Response, request, send_from_directory

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
BUILD_DIR = os.path.join(os.path.dirname(__file__), "react-app", "build")

app = Flask(__name__, static_folder=BUILD_DIR)


def _proxy(method: str, path: str, **kwargs) -> Response:
    url = f"{API_BASE_URL}{path}"
    if request.args:
        kwargs.setdefault("params", request.args.to_dict())
    try:
        resp = requests.request(method, url, timeout=60, **kwargs)
        return Response(
            resp.content,
            status=resp.status_code,
            content_type=resp.headers.get("content-type", "application/json"),
        )
    except requests.exceptions.ConnectionError:
        return Response('{"detail":"Backend unavailable"}', status=503, content_type="application/json")


@app.route("/api/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def api_proxy(path: str):
    kwargs = {}
    if request.method in ("POST", "PUT") and request.is_json:
        kwargs["json"] = request.get_json()
    return _proxy(request.method, f"/{path}", **kwargs)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path: str):
    if path and os.path.exists(os.path.join(BUILD_DIR, path)):
        return send_from_directory(BUILD_DIR, path)
    return send_from_directory(BUILD_DIR, "index.html")
