"""WSGI application entrypoint for EcoFiber AI (Vercel Serverless & Local compatible)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))


def app(environ, start_response):
    """WSGI callable for Vercel Python runtime."""
    path = environ.get("PATH_INFO", "/")

    if path in ("/api/health", "/api"):
        status = "200 OK"
        headers = [
            ("Content-type", "application/json"),
            ("Access-Control-Allow-Origin", "*"),
        ]
        start_response(status, headers)
        data = {
            "status": "online",
            "app": "EcoFiber AI",
            "version": "0.1.0",
            "targets": [
                "tensile_strength",
                "flexural_strength",
                "impact_resistance",
                "water_absorption",
            ],
        }
        return [json.dumps(data, indent=2).encode("utf-8")]

    # Serve index.html WebAssembly Streamlit application
    index_file = ROOT / "index.html"
    if not index_file.is_file():
        index_file = ROOT / "public" / "index.html"

    if index_file.is_file():
        status = "200 OK"
        headers = [("Content-type", "text/html; charset=utf-8")]
        start_response(status, headers)
        return [index_file.read_bytes()]

    status = "200 OK"
    headers = [("Content-type", "text/plain")]
    start_response(status, headers)
    return [b"EcoFiber AI is ready."]


handler = app
