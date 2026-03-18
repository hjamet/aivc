"""
AIVC Web Dashboard mini-server (Phase 4).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from aivc.semantic.engine import SemanticEngine


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, engine=None, **kwargs):
        self.engine = engine
        # Serve static files from src/aivc/web/static
        static_dir = Path(__file__).parent / "static"
        super().__init__(*args, directory=str(static_dir), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == "/api/graph":
            self.send_json(self._api_graph())
            return
            
        if parsed.path == "/api/search":
            qs = parse_qs(parsed.query)
            query = qs.get("q", [""])[0]
            self.send_json(self._api_search(query))
            return
            
        # Default behavior: serve static files
        super().do_GET()

    def send_json(self, data: dict | list, status: int = 200):
        content = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _api_graph(self):
        """Return file nodes and co-occurrence edges."""
        nodes = self.engine.get_file_node_data()
        edges = self.engine.get_file_cooccurrences()
        return {"nodes": nodes, "edges": edges}

    def _api_search(self, query: str):
        """Return search results."""
        if not query:
            return []
            
        results = self.engine.search(query, top_n=20)
        out = []
        for r in results:
            out.append({
                "commit_id": r.commit_id,
                "title": r.title,
                "timestamp": r.timestamp,
                "score": r.score,
                "snippet": r.snippet,
                "file_paths": r.file_paths,
            })
        return out


def main():
    parser = argparse.ArgumentParser(description="AIVC Web Dashboard")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on (default 8765)")
    args = parser.parse_args()

    storage_root_str = os.environ.get("AIVC_STORAGE_ROOT")
    if not storage_root_str:
        print("[aivc] WARN: AIVC_STORAGE_ROOT not set, falling back to ~/.aivc/storage", file=sys.stderr)
        storage_root_str = str(Path.home() / ".aivc" / "storage")

    print(f"Loading AIVC SemanticEngine from {storage_root_str} ...")
    engine = SemanticEngine(Path(storage_root_str))

    def handler_factory(*args, **kwargs):
        return DashboardHandler(*args, engine=engine, **kwargs)

    server = HTTPServer(("localhost", args.port), handler_factory)
    print(f"✅ Dashboard running at http://localhost:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dashboard.")
        server.server_close()


if __name__ == "__main__":
    main()
