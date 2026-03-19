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

### Fichiers Consultés (Consulted Files)

Lorsque vous créez un commit, vous pouvez spécifier une liste de `consulted_files`.
Ce sont des fichiers que vous avez lus et qui vous ont été **véritablement utiles** pour
accomplir votre tâche (ex: référence technique, exemple de code, documentation interne),
mais que vous n'avez pas modifiés.

**RÈGLE D'OR** : Ne mentionnez QUE les documents contenant des informations que vous ne
connaissiez pas avant de les avoir lus. N'ajoutez pas de fichiers par "politesse" ou 
utilité de surface. Cela polluerait votre mémoire à long terme.

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
| `untrack` | **DESTRUCTIVE** — remove a file from tracking and erase its entire history. |
| `track` | Add new files to AIVC tracking (file, directory, or glob pattern). |
| `watch_directory` | Start real-time surveillance of a directory (automatic tracking of new files). |
| `get_watched_directories` | List directories currently under AIVC surveillance. |
| `search_files_bm25` | Lexical search (BM25) over current tracked file contents. |

## `untrack` Warning

`untrack(file_path)` is irreversible. It erases all stored blobs and history
for that file. Use it only to free storage on files you are certain you no
longer need to track.
"""

# ---------------------------------------------------------------------------
# Bootstrap — engine initialisation
# ---------------------------------------------------------------------------

from aivc.config import get_storage_root

_storage_root = get_storage_root()

# SemanticEngine is imported here (triggering a fast eager init of Workspace +
# SQLite graph; the heavy ML components remain lazy until first use).
from aivc.semantic.engine import SemanticEngine  # noqa: E402

_engine = SemanticEngine(_storage_root)

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP(name="aivc", instructions=_SYSTEM_PROMPT)

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
        consulted_files: Optional list of tracked files that were consulted and
                         provided CRUCIAL context for this task, but not modified.

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
def search_memory(query: str, top_n: int = 5, filter_glob: str = "") -> str:
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

    Returns:
        A ranked list of matching commits + the most relevant file paths.
    """
    top_n = min(top_n, 20)
    results = _engine.search(query, top_n=top_n, filter_glob=filter_glob)

    if not results:
        return "No matching commits found in memory."

    # Build commit list
    commit_lines = []
    for i, r in enumerate(results, 1):
        commit_lines.append(
            f"{i}. [{r.timestamp[:10]}] {r.title}\n"
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
        file_lines.append(f"  - {fp} (in {count}/{len(results)} results)")

    output = "## Matching Commits\n\n"
    output += "\n".join(commit_lines)

    if file_lines:
        output += "\n\n## Most Relevant Files\n"
        output += "\n".join(file_lines)
    else:
        output += "\n\n(No file associations found for these commits.)"

    output += "\n\n💡 Use `consult_commit(commit_id)` to read a full note."
    return output


@mcp.tool()
def search_files_bm25(query: str, top_n: int = 5) -> str:
    """Search for keywords or exact code patterns in current tracked files.

    Uses BM25 (lexical ranking) on the actual text content of files currently
    on disk. This is the only tool that searches INSIDE the code/files.

    Args:
        query: Keywords or code fragment (e.g. "function_name" or "import os").
        top_n: Number of results to return (default 5).

    Returns:
        A list of matching files with their relative paths and context snippets.
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

    changes_summary = (
        "\n".join(
            f"  - [{c.action}] {c.path}" + (f" ({c.format_impact()})" if c.action != "consulted" else "")
            for c in commit.changes
        )
        if commit.changes
        else "  (no file changes recorded)"
    )

    return (
        f"# Commit: {commit.title}\n\n"
        f"**ID**        : {commit.id}\n"
        f"**Timestamp** : {commit.timestamp}\n"
        f"**Parent**    : {commit.parent_id or 'none (initial commit)'}\n\n"
        f"{context_block}"
        f"## Files Changed\n{changes_summary}\n\n"
        f"## Note\n\n{commit.note}"
    )


@mcp.tool()
def get_recent_commits(limit: int = 10, offset: int = 0) -> str:
    """Display the recent commit history (like `git log`).

    Use this tool at the start of a session or when you need to recall what
    was done recently without having a specific search query.
    Results are in reverse chronological order (newest first).
    Use `offset` and `limit` to paginate (e.g. offset=10 to see commits 11-20).

    Args:
        limit:  Number of commits to show (default 10, max 50).
        offset: Number of commits to skip from the most recent (default 0).

    Returns:
        A formatted list of recent commits with their associated file paths.
    """
    limit = min(limit, 50)

    # get_log fetches `offset + limit` commits and then slices.
    all_recent = _engine.get_log(limit=offset + limit)
    page = all_recent[offset : offset + limit]

    if not page:
        return "No commits found in this range."

    lines = [f"Showing commits {offset + 1}–{offset + len(page)} (newest first)\n"]
    for i, commit in enumerate(page, offset + 1):
        try:
            files = _engine.get_commit_files(commit.id)
            files_str = ", ".join(files) if files else "—"
        except KeyError:
            files_str = "—"

        lines.append(
            f"{i:>3}. [{commit.timestamp[:10]}] {commit.title}\n"
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

    Args:
        file_path: The path of the file to read.
        commit_id: The UUID of the commit at which to read the file.

    Returns:
        The UTF-8 decoded content of the file at that point in time.

    Raises:
        KeyError: If the file or commit is not found in history.
        UnicodeDecodeError: If the file content is not valid UTF-8.
    """
    raw: bytes = _engine.read_file_at_commit(file_path, commit_id)
    return raw.decode("utf-8")


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
def untrack(file_path: str) -> str:
    """⚠️ DESTRUCTIVE — Remove a file from AIVC tracking and erase its full history.

    This operation:
    1. Removes the file from the tracked files list.
    2. Decrements blob reference counts for every historical version of the file.
    3. Physically deletes blobs whose reference count drops to zero (Garbage Collection).
    4. Strips the file's `FileChange` entries from all existing commits.

    This action is IRREVERSIBLE. All stored history for this file will be lost.
    Use this only to free storage when you are certain you no longer need the
    history for a given file.

    Args:
        file_path: The exact path of the file to untrack (as shown in `get_status`).

    Returns:
        Confirmation message.

    Raises:
        KeyError: If the file is not currently tracked.
    """
    _engine.untrack(file_path)
    return (
        f"🗑️  File untracked and history erased: {file_path}\n"
        "All associated blobs have been garbage-collected."
    )


@mcp.tool()
def track(path: str) -> str:
    """Add files to AIVC tracking.

    Accepts a file path, directory path, or glob pattern.
    Paths are resolved to absolute paths relative to the current working directory.

    Args:
        path: File, directory, or glob pattern to track.

    Returns:
        Confirmation with the list of newly tracked files.

    Raises:
        ValueError: If no files match the given path/pattern.
    """
    result = _engine.track(path)
    newly_tracked = result["newly_tracked"]
    hidden_skipped = result["hidden_skipped"]

    if not newly_tracked:
        msg = "No new files to track (already tracked or no match)."
        if hidden_skipped > 0:
            msg += f" ({hidden_skipped} hidden files were ignored)."
        return msg

    lines = [f"✅ Tracked {len(newly_tracked)} new file(s):"]
    for f in newly_tracked:
        lines.append(f"  + {f}")

    if hidden_skipped > 0:
        lines.append(f"\n💡 {hidden_skipped} hidden files/folders were ignored.")
    
    lines.append("\n💡 PRO-TIP: Use `untrack` on any useless files (build artifacts, etc.) to keep your memory relevant.")

    return "\n".join(lines)


@mcp.tool()
def watch_directory(path: str, ignores: list[str] = []) -> str:
    """Start real-time surveillance of a directory.

    Any new file created in this directory (or its subdirectories) will be
    automatically added to AIVC tracking. Hidden files/folders are ignored.
    This also performs an immediate initial scan and tracking of existing files.

    Args:
        path: Absolute path to the directory to watch.
        ignores: Optional list of glob patterns to ignore.
    """
    result = _engine.watch(path, ignores=ignores)
    newly_tracked = result["newly_tracked"]
    hidden_skipped = result["hidden_skipped"]

    lines = [f"🔭 Surveillance started for: {path}"]
    if newly_tracked:
        lines.append(f"✅ Tracked {len(newly_tracked)} existing file(s).")
    else:
        lines.append("No new files found in initial scan.")

    if hidden_skipped > 0:
        lines.append(f"💡 {hidden_skipped} hidden files were ignored.")

    return "\n".join(lines)


@mcp.tool()
def get_watched_directories() -> str:
    """List all directories currently under real-time surveillance."""
    watched = _engine.get_watched_dirs()
    if not watched:
        return "No directories are currently under real-time surveillance."

    lines = ["## Watched Directories\n"]
    for path, cfg in watched.items():
        ignores = cfg.get("ignores", [])
        lines.append(f"- `{path}`" + (f" (ignores: {', '.join(ignores)})" if ignores else ""))

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
    if not _WATCHDOG_AVAILABLE:
        print("⚠️  'watchdog' library not found. Real-time surveillance disabled.", file=sys.stderr)
        return None

    watched_dirs = _engine.get_watched_dirs()
    if not watched_dirs:
        return None

    observer = Observer()
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
            observer.schedule(handler, path, recursive=True)
            count += 1
    
    if count > 0:
        observer.daemon = True
        observer.start()
        print(f"🔭 Started background surveillance on {count} directory/ies.", file=sys.stderr)
        return observer
    return None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Start background tasks
    _observer = start_background_watchers()
    
    # Run MCP server
    mcp.run(transport="stdio")
