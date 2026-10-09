"""Vercel serverless function entrypoint for EcoFiber AI."""

import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))


class handler(BaseHTTPRequestHandler):
    """Vercel HTTP request handler."""

    def do_GET(self):
        if self.path.startswith("/api/health") or self.path == "/api":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            data = {
                "status": "online",
                "app": "EcoFiber AI",
                "version": "0.1.0",
                "deployment": "Vercel Serverless + WebAssembly Stlite",
                "targets": [
                    "tensile_strength",
                    "flexural_strength",
                    "impact_resistance",
                    "water_absorption",
                ],
            }
            self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))
            return

        # Serve static WebAssembly Streamlit application
        index_file = ROOT / "public" / "index.html"
        if not index_file.is_file():
            index_file = ROOT / "index.html"

        if index_file.is_file():
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(index_file.read_bytes())
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"EcoFiber AI is online. Please load the dashboard index.")
