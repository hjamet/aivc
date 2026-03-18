"""
AIVC Command Line Interface.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# SemanticEngine is imported inside `main()` after we check AIVC_STORAGE_ROOT
# to keep CLI fast and error out early if the env var is missing.

# ---------------------------------------------------------------------------
# ANSI Formatting helpers
# ---------------------------------------------------------------------------
CYAN = "\033[0;36m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _format_bytes(n: int | None) -> str:
    if n is None:
        return "missing"
    if n < 1024:
        return f"{n} B"
    if n < 1024**2:
        return f"{n / 1024:.1f} KB"
    return f"{n / 1024**2:.1f} MB"


def _get_engine() -> "SemanticEngine":
    """Instantiate the SemanticEngine from AIVC_STORAGE_ROOT."""
    storage_root_str = os.environ.get("AIVC_STORAGE_ROOT")
    if not storage_root_str:
        sys.exit(
            f"{BOLD}\033[31m[aivc] ERROR:{RESET} Environment variable 'AIVC_STORAGE_ROOT' is not set.\n"
            "Cannot start AIVC CLI. Run install.sh to configure it or set the variable manually."
        )

    from aivc.semantic.engine import SemanticEngine
    return SemanticEngine(Path(storage_root_str))

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_status(args: argparse.Namespace) -> None:
    engine = _get_engine()
    statuses = engine.get_status()

    if not statuses:
        print("No files are currently tracked by AIVC.")
        return

    header = f"{CYAN}{'File Path':<60} {'Current':>10} {'History':>10}{RESET}"
    print(header)
    print("-" * 82)
    
    for s in statuses:
        curr = _format_bytes(s.current_size)
        hist = _format_bytes(s.history_size)
        print(f"{s.path:<60} {curr:>10} {hist:>10}")
        
    print("-" * 82)
    print(f"Total tracked: {len(statuses)} file(s)")


def cmd_log(args: argparse.Namespace) -> None:
    engine = _get_engine()
    commits = engine.get_log(limit=args.limit)
    
    if not commits:
        print("No commits found in memory.")
        return

    for c in commits:
        files = engine.get_commit_files(c.id)
        files_str = ", ".join(files) if files else "—"

        print(f"{YELLOW}commit {c.id}{RESET}")
        print(f"{DIM}Date:{RESET}    {c.timestamp}")
        print(f"{DIM}Files:{RESET}   {files_str}")
        print(f"\n    {BOLD}{c.title}{RESET}\n")


def cmd_search(args: argparse.Namespace) -> None:
    engine = _get_engine()
    print(f"{DIM}Searching memory for: '{args.query}'...{RESET}\n")
    
    results = engine.search(args.query, top_n=args.top_n)
    
    if not results:
        print("No matching commits found.")
        return

    for i, r in enumerate(results, 1):
        print(f"{CYAN}{BOLD}{i}. {r.title}{RESET} {DIM}(score: {r.score:.3f}){RESET}")
        print(f"   {DIM}ID:{RESET}    {r.commit_id}")
        print(f"   {DIM}Date:{RESET}  {r.timestamp}")
        print(f"   {DIM}Files:{RESET} {', '.join(r.file_paths) if r.file_paths else '—'}")
        print(f"\n      {r.snippet}\n")

def cmd_web(args: argparse.Namespace) -> None:
    """Launch the Web Dashboard server."""
    from aivc.web.dashboard import main as dashboard_main
    # Override sys.argv so dashboard's own argparse picks up the port
    sys.argv = ["aivc-web", "--port", str(args.port)]
    dashboard_main()

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="AIVC — AI Version Control CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    subparsers.add_parser(
        "status", 
        help="List all tracked files with storage usage"
    )

    # log
    parser_log = subparsers.add_parser(
        "log", 
        help="Show recent commit history"
    )
    parser_log.add_argument(
        "-n", "--limit", type=int, default=10, 
        help="Number of commits to show (default: 10)"
    )

    # search
    parser_search = subparsers.add_parser(
        "search", 
        help="Semantic search over past commits"
    )
    parser_search.add_argument(
        "query", type=str, 
        help="Natural language query"
    )
    parser_search.add_argument(
        "-n", "--top-n", type=int, default=5, 
        help="Number of results to return (default: 5)"
    )

    # web
    parser_web = subparsers.add_parser(
        "web",
        help="Launch the interactive Web Dashboard"
    )
    parser_web.add_argument(
        "-p", "--port", type=int, default=8765,
        help="Port to serve the dashboard on (default: 8765)"
    )

    args = parser.parse_args()

    if args.command == "status":
        cmd_status(args)
    elif args.command == "log":
        cmd_log(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "web":
        cmd_web(args)


if __name__ == "__main__":
    main()

