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

    def do_HEAD(self):
        parsed = urlparse(self.path)
        
        if parsed.path in ("/api/graph", "/api/search"):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            return
            
        super().do_HEAD()

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

        if parsed.path == "/api/log":
            qs = parse_qs(parsed.query)
            offset = int(qs.get("offset", ["0"])[0])
            limit = int(qs.get("limit", ["10"])[0])
            self.send_json(self._api_log(offset=offset, limit=limit))
            return

        if parsed.path.startswith("/api/memory/"):
            memory_id = parsed.path[len("/api/memory/"):]
            self.send_json(self._api_memory(memory_id))
            return

        if parsed.path.startswith("/api/file-history/"):
            import urllib.parse
            # The path might be url-encoded (e.g. spaces, slashes)
            file_path = urllib.parse.unquote(parsed.path[len("/api/file-history/"):])
            self.send_json(self._api_file_history(file_path))
            return
            
        # Default behavior: serve static files
        super().do_GET()

    def send_json(self, data: dict | list, status: int = 200):
        content = json.dumps(data).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except (ConnectionResetError, BrokenPipeError):
            # Client disconnected prematurely, harmless.
            pass

    def _api_graph(self):
        """Return file nodes and co-occurrence edges."""
        edges = self.engine.get_file_cooccurrences()
        # Only send nodes that participate in at least one edge
        connected_files = set()
        for e in edges:
            connected_files.add(e["source"])
            connected_files.add(e["target"])
        nodes = self.engine.get_file_node_data(connected_files=connected_files)
        return {"nodes": nodes, "edges": edges}

    def _api_search(self, query: str):
        """Return search results."""
        if not query:
            return []
            
        results = self.engine.search(query, top_n=20)
        out = []
        for r in results:
            out.append({
                "memory_id": r.memory_id,
                "title": r.title,
                "timestamp": r.timestamp,
                "score": r.score,
                "snippet": r.snippet,
                "file_paths": r.file_paths,
            })
        return out

    def _api_memory(self, memory_id: str):
        """Return full memory details."""
        try:
            memory = self.engine.get_memory(memory_id)
            if not memory:
                return {"error": f"Memory {memory_id} not found"}
        except (KeyError, FileNotFoundError):
            return {"error": f"Memory {memory_id} not found"}
        return {
            "id": memory.id,
            "title": memory.title,
            "timestamp": memory.timestamp,
            "note": memory.note,
            "changes": [
                {
                    "path": c.path,
                    "action": c.action,
                    "size_before": c.bytes_removed,
                    "size_after": c.bytes_added,
                }
                for c in memory.changes
            ],
        }

    def _api_log(self, offset: int = 0, limit: int = 10):
        """Return paginated memory log."""
        memories = self.engine.get_log(limit=limit, offset=offset)
        out = []
        for c in memories:
            out.append({
                "id": c.id,
                "title": c.title,
                "timestamp": c.timestamp,
                "file_count": len(c.changes),
            })
        return out

    def _api_file_history(self, file_path: str):
        """Return commit history for a specific file."""
        try:
            history = self.engine.get_file_history(file_path)
            return history
        except KeyError:
            return {"error": f"File {file_path} not found in history."}


def main():
    parser = argparse.ArgumentParser(description="AIVC Web Dashboard")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on (default 8765)")
    args = parser.parse_args()

    from aivc.config import get_storage_root
    storage_root = get_storage_root(allow_fallback=True)

    print(f"Loading AIVC SemanticEngine from {storage_root} ...")
    engine = SemanticEngine(storage_root)

    def handler_factory(*args, **kwargs):
        return DashboardHandler(*args, engine=engine, **kwargs)

    port = args.port
    server = None
    for p in range(args.port, args.port + 20):
        try:
            server = HTTPServer(("localhost", p), handler_factory)
            port = p
            break
        except OSError as e:
            if getattr(e, "errno", 0) == 98 or "already in use" in str(e):
                continue
            raise

    if not server:
        print(f"[aivc] FATAL: Could not find an open port in range {args.port}-{args.port+19}", file=sys.stderr)
        sys.exit(1)

    print(f"✅ Dashboard running at http://localhost:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down dashboard.")
        server.server_close()


if __name__ == "__main__":
    main()

