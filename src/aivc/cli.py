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
    result = engine.track(args.path, ignores=args.ignore)
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


def cmd_config(args: argparse.Namespace) -> None:
    """Manage AIVC configuration."""
    from aivc.config import get_aivc_config, save_aivc_config
    config = get_aivc_config()

    if args.key and args.value:
        # Simple nested key support (e.g. sync.enabled)
        parts = args.key.split(".")
        target = config
        for p in parts[:-1]:
            if p not in target: target[p] = {}
            target = target[p]
        
        # Type conversion attempt
        val = args.value
        if val.lower() == "true": val = True
        elif val.lower() == "false": val = False
        elif val.isdigit(): val = int(val)
        
        target[parts[-1]] = val
        save_aivc_config(config)
        print(f"{GREEN}Config updated: {args.key} = {val}{RESET}")
    else:
        import json
        print(f"{YELLOW}{BOLD}Current AIVC Configuration:{RESET}")
        print(json.dumps(config, indent=2))


def cmd_sync_setup(args: argparse.Namespace) -> None:
    """Guide the user through rclone sync setup."""
    from aivc.config import get_aivc_config, save_aivc_config, get_rclone_exe
    import subprocess
    
    config = get_aivc_config()
    if "sync" not in config: config["sync"] = {}
    
    print(f"{CYAN}{BOLD}=== AIVC Cloud Sync Setup ==={RESET}")
    print("This will configure rclone to sync your memory between machines.")
    
    rclone = get_rclone_exe()
    print(f"\n1. {BOLD}Rclone binary:{RESET} {rclone}")
    
    print(f"\n2. {BOLD}Remote Configuration:{RESET}")
    print("You must first create a remote named 'aivc_remote' (or your choice) via 'rclone config'.")
    print("We recommend Google Drive, but any rclone-supported backend works.")
    
    remote_name = input(f"Enter your rclone remote name (default: {config['sync'].get('remote_name', 'aivc_remote')}): ").strip()
    if remote_name: config["sync"]["remote_name"] = remote_name
    elif "remote_name" not in config["sync"]: config["sync"]["remote_name"] = "aivc_remote"

    enabled = input("Enable cloud sync? (y/n, default: y): ").strip().lower() != 'n'
    config["sync"]["enabled"] = enabled

    save_aivc_config(config)
    print(f"\n{GREEN}Success! Configuration saved to ~/.aivc/config.json{RESET}")
    if enabled:
        print(f"{YELLOW}Cloud sync is now ENABLED.{RESET}")
    else:
        print(f"{DIM}Cloud sync is currently DISABLED.{RESET}")


def cmd_sync_status(args: argparse.Namespace) -> None:
    """Show cloud sync status and remote machines."""
    from aivc.config import get_aivc_config, get_machine_id
    from aivc.sync.sync import RcloneSyncManager
    
    config = get_aivc_config()
    sync_cfg = config.get("sync", {})
    m_id = get_machine_id()
    
    print(f"{CYAN}{BOLD}AIVC Sync Status:{RESET}")
    print(f"  {BOLD}Local Machine ID:{RESET} {m_id}")
    print(f"  {BOLD}Sync Enabled:{RESET}     {GREEN if sync_cfg.get('enabled') else YELLOW}{sync_cfg.get('enabled', False)}{RESET}")
    print(f"  {BOLD}Remote Name:{RESET}      {sync_cfg.get('remote_name', '—')}")
    
    if sync_cfg.get("enabled"):
        try:
            manager = RcloneSyncManager(Path.home() / ".aivc" / "storage")
            print(f"\n{DIM}Checking remote machines via rclone...{RESET}")
            # list dirs in AIVC_Sync/
            remote = sync_cfg.get("remote_name")
            res = manager._run_rclone(["lsf", f"{remote}:AIVC_Sync/"], check=False)
            if res.returncode == 0:
                others = [d.rstrip('/') for d in res.stdout.splitlines() if d.rstrip('/') != m_id]
                print(f"  {BOLD}Remote machines seen:{RESET} {', '.join(others) if others else 'none yet'}")
                
                # Auto-update remote_machines list in config if needed
                if set(others) != set(sync_cfg.get("remote_machines", [])):
                    config["sync"]["remote_machines"] = list(set(others))
                    from aivc.config import save_aivc_config
                    save_aivc_config(config)
                    print(f"{DIM}(Updated remote_machines list in config){RESET}")
            else:
                print(f"{RED}Error connecting to remote: {res.stderr.strip()}{RESET}")
        except Exception as e:
            print(f"{RED}Error: {e}{RESET}")

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
    parser_track.add_argument(
        "--ignore", type=str, nargs="+", default=[],
        help="Optional glob patterns to ignore (only when tracking a directory)"
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

    # config
    parser_config = subparsers.add_parser(
        "config",
        help="Manage AIVC configuration"
    )
    parser_config.add_argument("key", type=str, nargs="?", help="Config key (path.to.key)")
    parser_config.add_argument("value", type=str, nargs="?", help="New value")

    # sync
    parser_sync = subparsers.add_parser(
        "sync",
        help="Manage cloud synchronization"
    )
    sync_sub = parser_sync.add_subparsers(dest="sync_command", required=True)
    sync_sub.add_parser("setup", help="Interactive rclone sync setup")
    sync_sub.add_parser("status", help="Check cloud sync status")

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
    elif args.command == "config":
        cmd_config(args)
    elif args.command == "sync":
        if args.sync_command == "setup":
            cmd_sync_setup(args)
        elif args.sync_command == "status":
            cmd_sync_status(args)


if __name__ == "__main__":
    main()
