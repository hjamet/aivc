"""
AIVC MCP Server — Long-term memory for LLM agents.

Exposes the SemanticEngine as a set of MCP tools via FastMCP (stdio transport).
The server is started by: ``python -m aivc.server``

Environment variables:
    AIVC_STORAGE_ROOT  (required) — absolute path to the AIVC data directory.
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# System prompt — injected into every LLM context using this server
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """
# AIVC — AI Version Control (Long-Term Memory)

You have access to a persistent, versioned memory system called AIVC.
AIVC is your long-term memory. Use it actively — it is the only way to preserve
context beyond a single conversation.

## Core Concept

AIVC stores **commits**: a short title + a detailed Markdown note you write yourself.
Every commit also automatically snapshots any tracked files that were modified.
Commits are indexed semantically, so you can retrieve them by meaning later.

## CRITICAL RULE — COMMIT OFTEN

**You MUST create a commit after EVERY significant step.**

A commit is required after:
- Completing a sub-task or an entire task.
- Creating or modifying any artifact (file, script, document, test, config…).
- Discovering a key finding or making an architectural decision.
- Finishing any phase of a plan, even if work is still ongoing.
- Any identifiable "checkpoint" in your reasoning.

The commit note must be **detailed**. Do not write one-liners.
Document your reasoning, the decisions made, the problems encountered,
and the solutions found. Think of it as a handover memo to your future self.

### Consulted Files

When you create a commit, you can specify a list of `consulted_files`.
These are files you have read and that were **truly useful** to you to
accomplish your task (e.g., technical reference, code example, internal documentation),
but that you did not modify. Untracked files will be auto-tracked if they
exist on disk; non-existent files are silently ignored.

**GOLDEN RULE**: Mention ONLY those documents containing information that you
did not know before reading them. Do not add files for "politeness" or 
surface utility. This would pollute your long-term memory.

## Recall Funnel

To retrieve memory, follow this two-step funnel:

1. **`search_memory`** — for semantic search by meaning (idea, topic, solution).
   → Returns commit titles/dates/IDs + the most relevant file paths. NEVER the full note.
2. **`get_recent_commits`** — for recalling recent history without a specific query.
   → Returns the last N commits with their files (chronological).
3. **`consult_commit`** — to read the full note of a specific commit.
   → Call this AFTER identifying a relevant commit via `search_memory` or `get_recent_commits`.

4. **`search_files_bm25`** — for keyword search in the CURRENT state of files.
   → This is the ONLY tool to search inside file contents. Use it for finding exact functions, variables, or code patterns.
   → Unlike `search_memory` (semantic search in *past commit notes*), `search_files_bm25` looks at what is *currently* on disk for tracked files.

## Tool Reference

| Tool | Purpose |
|------|---------|
| `create_commit` | Save a memory checkpoint. Call this VERY often. |
| `search_memory` | Semantic search over all past commit notes. |
| `get_recent_commits` | Recent commit log (paginable). |
| `consult_commit` | Read a specific commit note in full. |
| `consult_file` | Get the AIVC history of a specific file (which commits touched it). |
| `read_historical_file` | Read the content of a file as it was at a specific past commit. |
| `get_status` | List tracked files with current size and history weight. |
| `untrack` | **⚠️ VERY DESTRUCTIVE** — Accepts a **list** of paths/globs. STOPS surveillance and ERASES full history. |
| `track` | Accepts a **list** of file paths, directory paths, or glob patterns. Directories start continuous surveillance. |
| `search_files_bm25` | Lexical search (BM25) over current tracked file contents. |

## `untrack` Warning

`untrack([paths])` is HIGHLY DESTRUCTIVE. Do NOT use it blindly.
- If called on a file, it erases the file's entire history and blobs.
- If called on a directory, it STOPS tracking it, AND PERMANENTLY ERASES THE HISTORY OF ALL FILES INSIDE IT.
Do NOT use `untrack` without exploring `consult_file` or `search_memory` first to guarantee the files are truly useless.
"""

# ---------------------------------------------------------------------------
# Bootstrap — engine initialisation
# ---------------------------------------------------------------------------

from aivc.config import get_storage_root

_storage_root = get_storage_root()

# SemanticEngine is imported here (triggering a fast eager init of Workspace +
# SQLite graph; the heavy ML components remain lazy until first use).
from aivc.semantic.engine import SemanticEngine  # noqa: E402
from aivc.sync.sync import RcloneSyncManager
from aivc.sync.background import BackgroundSyncer
from aivc.config import get_machine_id

_engine = SemanticEngine(_storage_root)
_sync_manager = RcloneSyncManager(_storage_root)
_syncer = BackgroundSyncer(_storage_root)

_local_machine_id = get_machine_id()

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP(name="aivc", instructions=_SYSTEM_PROMPT)
_observer = None

# ---------------------------------------------------------------------------
# Helper formatting functions
# ---------------------------------------------------------------------------


def _format_bytes(n: int) -> str:
    """Format a byte count as a human-readable string."""
    if n < 1024:
        return f"{n} B"
    if n < 1024 ** 2:
        return f"{n / 1024:.1f} KB"
    return f"{n / 1024 ** 2:.1f} MB"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def create_commit(title: str, note: str, consulted_files: list[str] = []) -> str:
    """Persist a memory checkpoint in AIVC.

    Call this tool after EVERY meaningful step: task completion, artefact creation,
    architectural decision, key discovery, or any checkpoint in your work.
    The note should be a rich, detailed Markdown document — your future self will
    read it to recall this moment. All tracked files that have changed since the last
    commit are automatically associated with this commit.

    Args:
        title: Short, descriptive title (e.g. "Implemented user auth module").
        note: Detailed Markdown note documenting what was done, why, how, and any
              important context. The more detail, the better the future recall.
        consulted_files: Optional list of files that were consulted and
                         provided CRUCIAL context for this task, but not modified.
                         Files not yet tracked will be auto-tracked if they exist.

    Returns:
        Confirmation with the commit ID and the list of files that were snapshotted.

    Raises:
        RuntimeError: If no tracked file has changed and no files were consulted.
    """
    commit = _engine.create_commit(title, note, consulted_files=consulted_files)

    files_summary = (
        "\n".join(
            f"  - [{c.action}] {c.path}" + (f" ({c.format_impact()})" if c.action != "consulted" else "")
            for c in commit.changes
        )
        if commit.changes
        else "  (no tracked files changed)"
    )

    return (
        f"✅ Commit created successfully.\n"
        f"ID        : {commit.id}\n"
        f"Timestamp : {commit.timestamp}\n"
        f"Title     : {commit.title}\n"
        f"Files     :\n{files_summary}"
    )


@mcp.tool()
def search_memory(query: str, top_n: int = 5, filter_glob: str = "", only_local: bool = False) -> str:
    """Search past commit notes by semantic meaning.

    Uses a Bi-Encoder + Cross-Encoder pipeline to retrieve the most relevant
    commits for a natural-language query. Returns only commit metadata (ID,
    title, date, score) — never the full note content — to avoid context bloat.
    Also surfaces the files most frequently associated with the top results.

    Call `consult_commit(commit_id)` on a specific result to read its full note.

    Args:
        query: Free-text search query. Write it as a question or a short description.
        top_n: Number of results to return (default 5, max 20).
        filter_glob: Optional glob pattern (e.g. "src/*.py") to restrict search to commits
                     that touched matching files.
        only_local: If True, only search commits created on this machine.
    """
    top_n = min(top_n, 20)
    
    # Check if indexing is in progress
    indexing_queue_size = _engine.get_index_queue_size()
    warning_header = ""
    if indexing_queue_size > 0:
        warning_header = f"⚠️  Note: {indexing_queue_size} recent commit(s) are still being indexed and may be missing from search results.\n\n"

    results = _engine.search(query, top_n=top_n, filter_glob=filter_glob)

    if only_local:
        results = [r for r in results if getattr(r, 'machine_id', _local_machine_id) == _local_machine_id]

    if not results:
        return warning_header + "No matching commits found in memory."

    # Build commit list
    commit_lines = []
    for i, r in enumerate(results, 1):
        m_id = getattr(r, 'machine_id', "")
        remote_tag = f" [Remote: {m_id}]" if m_id and m_id != _local_machine_id else ""
        
        commit_lines.append(
            f"{i}. [{r.timestamp[:10]}] {r.title}{remote_tag}\n"
            f"   ID    : {r.commit_id}\n"
            f"   Score : {r.score:.3f}\n"
            f"   > {r.snippet}"
        )

    # Aggregate file paths across top results (most frequently mentioned)
    file_counter: Counter[str] = Counter()
    for r in results:
        file_counter.update(r.file_paths)

    file_lines = []
    for fp, count in file_counter.most_common(10):
        hint = ""
        # If results are remote, try to find local hints
        is_remote = any(getattr(r, 'machine_id', "") != _local_machine_id for r in results)
        if is_remote:
            local_match = _engine.find_local_equivalent(fp)
            if local_match:
                hint = f" (probablement `{local_match}` localement)"
        
        file_lines.append(f"  - {fp}{hint} (in {count}/{len(results)} results)")

    output = warning_header + "## Matching Commits\n\n"
    output += "\n".join(commit_lines)

    if file_lines:
        output += "\n\n## Most Relevant Files\n"
        output += "\n".join(file_lines)
    else:
        output += "\n\n(No file associations found for these commits.)"

    output += "\n\n💡 Use `consult_commit(commit_id)` to read a full note."
    return output


@mcp.tool()
def search_files_bm25(query: str, top_n: int = 5, only_local: bool = True) -> str:
    """Search for keywords or exact code patterns in current tracked files.

    Uses BM25 (lexical ranking) on the actual text content of files currently
    on disk. This is the only tool that searches INSIDE the code/files.

    Args:
        query: Keywords or code fragment (e.g. "function_name" or "import os").
        top_n: Number of results to return (default 5).
        only_local: (Ignored) BM25 search is always local as it looks at disk.
    """
    results = _engine.search_files_bm25(query, top_n=top_n)

    if not results:
        return f"No matches found for keyword query: '{query}'"

    lines = [f"## Lexical matches for: `{query}`\n"]
    for i, r in enumerate(results, 1):
        lines.append(
            f"{i}. `{r['path']}` (score: {r['score']:.3f})\n"
            f"   > {r['snippet']}"
        )

    return "\n".join(lines)


@mcp.tool()
def consult_commit(commit_id: str) -> str:
    """Read the full content of a specific commit.

    Returns the complete Markdown note written when the commit was created,
    along with a summary of the files that were changed (path, action, size impact).

    Args:
        commit_id: The UUID of the commit to read (obtained from `search_memory`
                   or `get_recent_commits`).

    Returns:
        The full Markdown note and the list of file changes.

    Raises:
        KeyError: If the commit_id does not exist.
    """
    commit = _engine.get_commit(commit_id)

    # Context (Prev/Next)
    prev_str = ""
    if commit.parent_id:
        try:
            parent = _engine.get_commit(commit.parent_id)
            prev_str = f"⬆️ **Prev** : {parent.title} (ID: {parent.id})\n"
        except KeyError:
            prev_str = f"⬆️ **Prev** : (metadata not found) (ID: {commit.parent_id})\n"

    next_str = ""
    try:
        child = _engine.find_child_commit(commit_id)
        if child:
            next_str = f"⬇️ **Next** : {child.title} (ID: {child.id})\n"
    except Exception:
        pass

    context_block = ""
    if prev_str or next_str:
        context_block = f"{prev_str}{next_str}\n"

    changes_summary = []
    for c in commit.changes:
        line = f"  - [{c.action}] {c.path}"
        if c.action != "consulted":
            line += f" ({c.format_impact()})"
        
        # Add local hint for remote commits
        if commit.machine_id and commit.machine_id != _local_machine_id:
            local_match = _engine.find_local_equivalent(c.path, c.blob_hash)
            if local_match:
                line += f" (probablement `{local_match}` localement)"
        
        changes_summary.append(line)
    
    changes_summary_str = "\n".join(changes_summary) if changes_summary else "  (no file changes recorded)"

    machine_line = ""
    if commit.machine_id and commit.machine_id != _local_machine_id:
        machine_line = f"**Machine**   : {commit.machine_id} (Distant)\n"

    return (
        f"# Commit: {commit.title}\n\n"
        f"**ID**        : {commit.id}\n"
        f"**Timestamp** : {commit.timestamp}\n"
        f"**Parent**    : {commit.parent_id or 'none (initial commit)'}\n"
        f"{machine_line}\n"
        f"{context_block}"
        f"## Files Changed\n{changes_summary}\n\n"
        f"## Note\n\n{commit.note}"
    )


@mcp.tool()
def get_recent_commits(limit: int = 10, offset: int = 0, only_local: bool = False) -> str:
    """Display the recent commit history (like `git log`).

    Use this tool at the start of a session or when you need to recall what
    was done recently without having a specific search query.
    Results are in reverse chronological order (newest first).
    Use `offset` and `limit` to paginate (e.g. offset=10 to see commits 11-20).

    Args:
        limit:  Number of commits to show (default 10, max 50).
        offset: Number of commits to skip from the most recent (default 0).
        only_local: If True, only show commits created on this machine.
    """
    limit = min(limit, 50)

    # get_log fetches `offset + limit` commits and then slices.
    all_recent = _engine.get_log(limit=offset + limit)
    
    if only_local:
        all_recent = [c for c in all_recent if c.machine_id == _local_machine_id]

    page = all_recent[offset : offset + limit]

    if not page:
        return "No commits found in this range."

    lines = [f"Showing commits {offset + 1}–{offset + len(page)} (newest first)\n"]
    for i, commit in enumerate(page, offset + 1):
        try:
            files = _engine.get_commit_files(commit.id)
            formatted_files = []
            for f in files:
                if commit.machine_id and commit.machine_id != _local_machine_id:
                    local_match = _engine.find_local_equivalent(f)
                    if local_match:
                        formatted_files.append(f"{f} (local: {Path(local_match).name})")
                        continue
                formatted_files.append(f)
            files_str = ", ".join(formatted_files) if formatted_files else "—"
        except KeyError:
            files_str = "—"

        m_tag = f" [Remote: {commit.machine_id}]" if commit.machine_id and commit.machine_id != _local_machine_id else ""
        lines.append(
            f"{i:>3}. [{commit.timestamp[:10]}] {commit.title}{m_tag}\n"
            f"      ID    : {commit.id}\n"
            f"      Files : {files_str}"
        )

    lines.append("\n💡 Use `consult_commit(commit_id)` to read a full commit note.")
    return "\n".join(lines)


@mcp.tool()
def consult_file(file_path: str) -> str:
    """Get the AIVC history of a specific file.

    Returns the list of commits that have ever touched this file,
    sorted from most recent to oldest based on graph order.
    This does NOT return the file's current content — use your text editor tools
    or `read_historical_file` for that.

    Args:
        file_path: The path of the file to look up (as tracked by AIVC).

    Returns:
        A list of commits that touched this file (ID, Date, Title).

    Raises:
        KeyError: If the file is not in the AIVC co-occurrence graph.
    """
    commit_ids = _engine.get_file_commits(file_path)

    if not commit_ids:
        return f"No commits found for file: {file_path}"

    lines = [f"## AIVC History for: `{file_path}`\n"]
    lines.append(f"{len(commit_ids)} commit(s) have touched this file:\n")

    for cid in commit_ids:
        try:
            commit = _engine.get_commit(cid)
            lines.append(
                f"  - [{commit.timestamp[:10]}] {commit.title}\n"
                f"    ID: {commit.id}"
            )
        except KeyError:
            lines.append(f"  - [unknown date] Commit {cid} (metadata not found)")

    lines.append(
        "\n💡 Use `consult_commit(commit_id)` to read the full note of a specific commit."
        "\n💡 Use `read_historical_file(file_path, commit_id)` to read the file content at that commit."
    )
    return "\n".join(lines)


@mcp.tool()
def read_historical_file(file_path: str, commit_id: str) -> str:
    """Read the content of a tracked file as it was at a specific past commit.

    Scans the commit chain backwards from `commit_id` to find the most recent
    blob for `file_path` at or before that commit.

    If the file content exists only on a remote machine, it will be downloaded
    automatically if cloud sync is enabled.

    Args:
        file_path: The path of the file to read.
        commit_id: The UUID of the commit at which to read the file.
    """
    warning_header = ""
    try:
        raw: bytes = _engine.read_file_at_commit(file_path, commit_id)
    except FileNotFoundError:
        # If the file hasn't been found locally, it might be a distant blob.
        # Find which commit exactly has this blob to know the machine_id.
        commit = _engine.get_commit(commit_id)
        target_commit = None
        target_blob_hash = None
        
        # Walk back to find the blob hash
        cid = commit_id
        while cid:
            c = _engine.get_commit(cid)
            for change in c.changes:
                if change.path == file_path and change.blob_hash:
                    target_commit = c
                    target_blob_hash = change.blob_hash
                    break
            if target_commit: break
            cid = c.parent_id
            
        if target_commit and target_commit.machine_id and target_commit.machine_id != _local_machine_id:
            if not _sync_manager.enabled:
                raise RuntimeError(
                    f"File {file_path!r} exists only on remote machine {target_commit.machine_id!r} "
                    "and cloud sync is disabled."
                )
            
            # Show a warning to the agent
            warning_header = f"⚠️  [Remote: {target_commit.machine_id}] This file was downloaded from the cloud.\n"
            
            # Attempt to fetch
            _sync_manager.fetch_blob(target_blob_hash, target_commit.machine_id)
            # Try reading again
            raw = _engine.read_file_at_commit(file_path, commit_id)
        else:
            raise

    return warning_header + raw.decode("utf-8")


@mcp.tool()
def get_status() -> str:
    """List all files currently tracked by AIVC with their storage usage.

    Shows the current on-disk size of each tracked file and the total size
    of its historical blobs in AIVC storage. Use this to understand which
    files are consuming the most history space.

    Returns:
        A formatted table of tracked files with size information.
    """
    statuses = _engine.get_status()

    if not statuses:
        return "No files are currently tracked by AIVC."

    header = f"{'File Path':<60} {'Current':>10} {'History':>10}"
    separator = "-" * len(header)
    rows = [header, separator]

    for s in statuses:
        current = _format_bytes(s.current_size) if s.current_size is not None else "missing"
        history = _format_bytes(s.history_size)
        rows.append(f"{s.path:<60} {current:>10} {history:>10}")

    rows.append(separator)
    rows.append(f"Total tracked: {len(statuses)} file(s)")
    
    # Admonition for the LLM
    rows.append("\n💡 NOTE: Hidden files/folders (starting with '.') are NEVER tracked automatically.")
    rows.append("💡 PRO-TIP: If you see useless files (build artifacts, temp files), use `untrack(path)` IMMEDIATELY to keep memory clean.")
    
    return "\n".join(rows)


@mcp.tool()
def untrack(path_or_glob: list[str]) -> str:
    """⚠️ DESTRUCTIVE — Remove files or directories from AIVC tracking and erase their full history.

    This operation:
    1. Stops real-time surveillance (if directory).
    2. Removes matching files from the tracked list.
    3. Physically deletes blobs whose reference count drops to zero (Garbage Collection).
    4. Strips the files' `FileChange` entries from all existing commits.

    This action is IRREVERSIBLE. All stored history for these files will be lost.
    WARNING: Do NOT use this tool on a directory unless you are absolutely certain
    you want to destroy the history of ALL files inside it. NEVER use it without
    prior exploration of the file's usage (`consult_file` or `search_memory`).

    Args:
        path_or_glob: A list of exact paths, directories, or glob patterns to untrack.

    Returns:
        Confirmation message.

    Raises:
        KeyError: If no matching files or watched directories are found.
    """
    errors = []
    successes = []
    for p in path_or_glob:
        try:
            _engine.untrack(p)
            successes.append(p)
        except KeyError as e:
            errors.append(f"  ⚠️ {p}: {e}")

    lines = []
    if successes:
        lines.append(f"🗑️  Untracked and history erased for {len(successes)} path(s):")
        for s in successes:
            lines.append(f"  - {s}")
        lines.append("All associated blobs have been garbage-collected.")
    if errors:
        lines.append(f"\n⚠️ {len(errors)} path(s) could not be untracked:")
        lines.extend(errors)
    if not successes and not errors:
        lines.append("Nothing to untrack.")
    return "\n".join(lines)


@mcp.tool()
def track(path: list[str], ignores: list[str] = []) -> str:
    """Add files to AIVC tracking.

    Accepts a list of file paths, directory paths, or glob patterns.
    If a directory path is provided, it automatically starts real-time surveillance
    of that directory (any new files created inside will be tracked automatically).
    Hidden files/folders (starting with '.') are always ignored by default.

    Args:
        path: A list of file paths, directory paths, or glob patterns to track.
        ignores: Optional list of glob patterns to ignore (only applicable if watching a dir).

    Returns:
        Confirmation with the list of newly tracked files.

    Raises:
        ValueError: If no files match the given path/pattern.
    """
    all_newly_tracked = []
    total_hidden_skipped = 0
    errors = []

    for p in path:
        try:
            result = _engine.track(p, ignores)
            all_newly_tracked.extend(result["newly_tracked"])
            total_hidden_skipped += result["hidden_skipped"]

            global _observer
            if _WATCHDOG_AVAILABLE and _observer is not None and Path(p).is_dir():
                handler = AIVCWatcherHandler(_engine, p)
                _observer.schedule(handler, p, recursive=True)
        except ValueError as e:
            errors.append(f"  ⚠️ {p}: {e}")

    lines = []

    if not all_newly_tracked and not errors:
        msg = "No new files to track (already tracked or no match)."
        if total_hidden_skipped > 0:
            msg += f" ({total_hidden_skipped} hidden files were ignored)."
        lines.append(msg)
        return "\n".join(lines)

    if all_newly_tracked:
        lines.append(f"✅ Tracked {len(all_newly_tracked)} new file(s):")
        for f in all_newly_tracked:
            lines.append(f"  + {f}")

    if total_hidden_skipped > 0:
        lines.append(f"\n💡 {total_hidden_skipped} hidden files/folders were ignored.")

    if errors:
        lines.append(f"\n⚠️ {len(errors)} path(s) had issues:")
        lines.extend(errors)

    lines.append("\n💡 PRO-TIP: Use `untrack` on any useless files (build artifacts, etc.) to keep your memory relevant.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Background Watcher (watchdog)
# ---------------------------------------------------------------------------

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    _WATCHDOG_AVAILABLE = True
except ImportError:
    _WATCHDOG_AVAILABLE = False


class AIVCWatcherHandler(FileSystemEventHandler):
    """Handles real-time file creation events."""
    def __init__(self, engine, watched_path):
        self.engine = engine
        self.watched_path = Path(watched_path)

    def on_created(self, event):
        if event.is_directory:
            return
            
        # Dynamically check if this directory is still watched
        watched_dirs = self.engine.get_watched_dirs()
        abs_watched_path = str(self.watched_path.resolve())
        if abs_watched_path not in watched_dirs:
            return
        
        path = Path(event.src_path)
        # Check if hidden
        try:
            rel = path.relative_to(self.watched_path.parent)
            if any(part.startswith(".") for part in rel.parts):
                return
        except ValueError:
            # Fallback if path is outside (shouldn't happen with watchdogs)
            if any(part.startswith(".") for part in path.parts):
                return
            
        try:
            # Automatic track
            self.engine.track(str(path))
        except Exception:
            pass # Silent failure in background thread


def start_background_watchers():
    """Initialise and start background threads for watched directories."""
    global _observer
    if not _WATCHDOG_AVAILABLE:
        print("⚠️  'watchdog' library not found. Real-time surveillance disabled.", file=sys.stderr)
        return

    watched_dirs = _engine.get_watched_dirs()
    if not watched_dirs:
        return

    _observer = Observer()
    count = 0
    for path in watched_dirs:
        if os.path.isdir(path):
            # 1. Startup Sync (JIT track existing files)
            try:
                _engine.track(path)
            except Exception as e:
                print(f"⚠️  Startup sync failed for {path}: {e}", file=sys.stderr)

            # 2. Schedule watcher
            handler = AIVCWatcherHandler(_engine, path)
            _observer.schedule(handler, path, recursive=True)
            count += 1
    
    if count > 0:
        _observer.daemon = True
        _observer.start()
        print(f"🔭 Started background surveillance on {count} directory/ies.", file=sys.stderr)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Start background tasks
    start_background_watchers()
    _syncer.start()
    
    # Run MCP server
    mcp.run(transport="stdio")
