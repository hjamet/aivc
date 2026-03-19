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
    from aivc.config import get_storage_root
    storage_root = get_storage_root(allow_fallback=True)

    from aivc.semantic.engine import SemanticEngine
    return SemanticEngine(storage_root)

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

    # Watched directories (Phase 17)
    watched = engine.get_watched_dirs()
    if watched:
        print(f"\n{YELLOW}{BOLD}Watched Directories:{RESET}")
        for path, cfg in watched.items():
            ignores_str = f" (ignoring: {', '.join(cfg['ignores'])})" if cfg['ignores'] else ""
            print(f"  {CYAN}* {path}{RESET}{ignores_str}")


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
    if args.glob:
        print(f"{DIM}Searching memory for: '{args.query}' (filter: '{args.glob}')...{RESET}\n")
    else:
        print(f"{DIM}Searching memory for: '{args.query}'...{RESET}\n")
    
    results = engine.search(args.query, top_n=args.top_n, filter_glob=args.glob)
    
    if not results:
        print("No matching commits found.")
        return

    for i, r in enumerate(results, 1):
        print(f"{CYAN}{BOLD}{i}. {r.title}{RESET} {DIM}(score: {r.score:.3f}){RESET}")
        print(f"   {DIM}ID:{RESET}    {r.commit_id}")
        print(f"   {DIM}Date:{RESET}  {r.timestamp}")
        print(f"   {DIM}Files:{RESET} {', '.join(r.file_paths) if r.file_paths else '—'}")
        print(f"\n      {r.snippet}\n")


def cmd_search_files(args: argparse.Namespace) -> None:
    """Lexical search (BM25) over current tracked file contents."""
    engine = _get_engine()
    print(f"{DIM}Searching file contents for: '{args.query}' (BM25)...{RESET}\n")
    results = engine.search_files_bm25(args.query, top_n=args.top_n)
    
    if not results:
        print("No matching files found.")
        return

    for i, r in enumerate(results, 1):
        print(f"{CYAN}{BOLD}{i}. {r['path']}{RESET} {DIM}(score: {r['score']:.3f}){RESET}")
        print(f"   {r['snippet']}\n")

def cmd_track(args: argparse.Namespace) -> None:
    """Track a file, directory, or glob pattern."""
    engine = _get_engine()
    result = engine.track(args.path)
    newly_tracked = result["newly_tracked"]
    hidden_skipped = result["hidden_skipped"]

    if not newly_tracked:
        msg = f"{YELLOW}No new files to track{RESET} (already tracked or no match)."
        if hidden_skipped > 0:
            msg += f" {DIM}({hidden_skipped} hidden files ignored){RESET}"
        print(msg)
        return

    print(f"{GREEN}{BOLD}Tracked {len(newly_tracked)} new file(s):{RESET}")
    for f in newly_tracked:
        print(f"  {CYAN}+{RESET} {f}")
    
    if hidden_skipped > 0:
        print(f"{DIM}Note: {hidden_skipped} hidden files/folders were ignored.{RESET}")


def cmd_watch(args: argparse.Namespace) -> None:
    """Add a directory to surveillance."""
    engine = _get_engine()
    print(f"{DIM}Setting up surveillance for: {args.path}...{RESET}")
    result = engine.watch(args.path, ignores=args.ignore)
    newly_tracked = result["newly_tracked"]
    
    print(f"{GREEN}Surveillance active for {args.path}.{RESET}")
    if newly_tracked:
        print(f"{DIM}Tracked {len(newly_tracked)} existing file(s).{RESET}")
    
    if result["hidden_skipped"] > 0:
        print(f"{DIM}({result['hidden_skipped']} hidden files ignored){RESET}")


def cmd_unwatch(args: argparse.Namespace) -> None:
    """Stop surveillance for a directory."""
    engine = _get_engine()
    engine.unwatch(args.path)
    print(f"{YELLOW}Surveillance stopped for {args.path}.{RESET}")


def cmd_migrate(args: argparse.Namespace) -> None:
    """Explicitly migrate JSON commits to SQLite index."""
    print(f"{DIM}Checking for JSON commits to migrate to SQLite index...{RESET}")
    engine = _get_engine()
    engine.migrate_index()
    print(f"{GREEN}Migration complete.{RESET}")


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

    # migrate
    subparsers.add_parser(
        "migrate",
        help="Explicitly migrate JSON commits to SQLite index"
    )

    # track
    parser_track = subparsers.add_parser(
        "track",
        help="Track a file, directory, or glob pattern"
    )
    parser_track.add_argument(
        "path", type=str,
        help="File path, directory, or glob pattern to track"
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
    parser_search.add_argument(
        "-g", "--glob", type=str, default="", 
        help="Optional glob pattern to restrict search to matching files"
    )

    # search-files (BM25)
    parser_search_files = subparsers.add_parser(
        "search-files", 
        help="Lexical search (BM25) in current tracked files"
    )
    parser_search_files.add_argument(
        "query", type=str, 
        help="Keywords or exact terms to find"
    )
    parser_search_files.add_argument(
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

    # watch
    parser_watch = subparsers.add_parser(
        "watch",
        help="Watch a directory for new files"
    )
    parser_watch.add_argument(
        "path", type=str,
        help="Directory to watch"
    )
    parser_watch.add_argument(
        "--ignore", type=str, action="append",
        help="Glob pattern to ignore (optional, can be used multiple times)"
    )

    # unwatch
    parser_unwatch = subparsers.add_parser(
        "unwatch",
        help="Stop watching a directory"
    )
    parser_unwatch.add_argument(
        "path", type=str,
        help="Directory to unwatch"
    )

    args = parser.parse_args()

    if args.command == "status":
        cmd_status(args)
    elif args.command == "migrate":
        cmd_migrate(args)
    elif args.command == "track":
        cmd_track(args)
    elif args.command == "log":
        cmd_log(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "search-files":
        cmd_search_files(args)
    elif args.command == "web":
        cmd_web(args)
    elif args.command == "watch":
        cmd_watch(args)
    elif args.command == "unwatch":
        cmd_unwatch(args)


if __name__ == "__main__":
    main()

