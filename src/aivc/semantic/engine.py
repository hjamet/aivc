"""
SemanticEngine: orchestrates Workspace + Indexer + CooccurrenceGraph + Searcher.

This is the single public facade for Phase 2.  It wraps the Phase 1 Workspace
(keeping it pure stdlib) and adds semantic indexing transparently on every
``create_commit`` call.

Option B architecture: Workspace is *owned* by SemanticEngine; the core module
is never aware of ChromaDB or SentenceTransformers.

Lazy Loading: The Indexer (ChromaDB + SentenceTransformer) and Searcher
(CrossEncoder) are only instantiated on first use, keeping ``__init__`` fast
for CLI-style invocations that only need Workspace or Graph features.
"""

import threading
import queue
import time
import atexit
import os
from pathlib import Path
from typing import Any

from aivc.core.commit import Commit
from aivc.core.workspace import FileStatus, Workspace
from aivc.semantic.graph import CooccurrenceGraph
from aivc.config import get_machine_id
from aivc.sync.sync import RcloneSyncManager


class SemanticEngine:
    """High-level facade combining versioning + semantic search.

    Creates and owns:
    - A :class:`~aivc.core.workspace.Workspace` (Phase 1 core) — loaded eagerly
    - A :class:`~aivc.semantic.graph.CooccurrenceGraph` — loaded eagerly (SQLite, fast)
    - An :class:`~aivc.semantic.indexer.Indexer` (ChromaDB) — **lazy**
    - A :class:`~aivc.semantic.searcher.Searcher` (Cross-Encoder) — **lazy**

    All data is stored under ``storage_root``.
    """

    def __init__(self, storage_root: Path) -> None:
        """Initialise the lightweight sub-systems.

        Heavy ML dependencies (sentence-transformers, chromadb) are NOT loaded
        here.  They are loaded lazily on first ``create_commit`` or ``search``
        call.

        Args:
            storage_root: Single root directory for all AIVC data
                          (blobs, commits, ChromaDB, graph SQLite).
        """
        self._storage_root = storage_root
        self._workspace = Workspace(storage_root)
        self._graph = CooccurrenceGraph(storage_root)
        # Lazy — will be initialised on first access.
        self.__indexer = None
        self.__searcher = None
        self.__bm25_cache = None
        self._local_hints_index = None

        # Async Indexing & Sync
        self._index_queue = queue.Queue()
        self._sync_queue = queue.Queue()
        self._sync_manager = RcloneSyncManager(storage_root)
        
        self._indexing_thread = threading.Thread(target=self._indexing_worker_loop, daemon=True)
        self._sync_thread = threading.Thread(target=self._sync_worker_loop, daemon=True)
        
        self._indexing_thread.start()
        self._sync_thread.start()

        # Ensure graceful shutdown
        atexit.register(self.shutdown)

        # Register workspace reload callback
        self._workspace.register_reload_callback(self._on_workspace_reload)

    def _indexing_worker_loop(self):
        """Background worker thread to index commits from the queue."""
        while True:
            commit = self._index_queue.get()
            if commit is None: # Shutdown signal
                break
            try:
                # 1. Semantic indexing (triggers lazy load of indexer if needed)
                self._indexer.index_commit(commit)
                
                # 2. Forward to sync queue if enabled
                if self._sync_manager.enabled:
                    self._sync_queue.put(commit)
            except Exception as e:
                import sys
                print(f"Error in async indexing for commit {commit.id}: {e}", file=sys.stderr)
            finally:
                self._index_queue.task_done()

    def _sync_worker_loop(self):
        """Background worker thread to push commits/blobs to cloud."""
        while True:
            commit = self._sync_queue.get()
            if commit is None: # Shutdown signal
                break
            try:
                # Cloud Sync push
                self._sync_manager.push_commit(commit.id)
                for change in commit.changes:
                    if change.blob_hash:
                        self._sync_manager.push_blob(change.blob_hash)
            except Exception as e:
                import sys
                print(f"Error in async sync for commit {commit.id}: {e}", file=sys.stderr)
            finally:
                self._sync_queue.task_done()

    def shutdown(self, timeout: float = 5.0):
        """Signal workers to stop and wait for them to finish."""
        # 1. Signal indexing
        self._index_queue.put(None)
        # 2. Wait for indexing to finish (so it pushes remaining to sync)
        self._indexing_thread.join(timeout=timeout/2)
        
        # 3. Signal sync
        self._sync_queue.put(None)
        # 4. Wait for sync
        self._sync_thread.join(timeout=timeout/2)

    def get_index_queue_size(self) -> int:
        """Return the number of commits waiting to be indexed or synced."""
        return self._index_queue.qsize() + self._sync_queue.qsize()

    def _on_workspace_reload(self) -> None:
        """Callback from workspace when its state is reloaded from disk."""
        self._local_hints_index = None


    # ------------------------------------------------------------------
    # Lazy properties for heavy ML components
    # ------------------------------------------------------------------

    @property
    def _indexer(self):
        """Lazy-loaded Indexer (ChromaDB + SentenceTransformer bi-encoder)."""
        if self.__indexer is None:
            from aivc.semantic.indexer import Indexer
            self.__indexer = Indexer(self._storage_root)
        return self.__indexer

    @property
    def _searcher(self):
        """Lazy-loaded Searcher (Cross-Encoder reranking pipeline)."""
        if self.__searcher is None:
            from aivc.semantic.searcher import Searcher
            self.__searcher = Searcher(self._indexer)
        return self.__searcher

    @property
    def _bm25_cache(self):
        """Lazy-loaded BM25Cache (SQLite-backed tokenization cache)."""
        if self.__bm25_cache is None:
            from aivc.search.bm25_cache import BM25Cache
            self.__bm25_cache = BM25Cache(self._storage_root)
        return self.__bm25_cache

    # ------------------------------------------------------------------
    # Commit lifecycle
    # ------------------------------------------------------------------

    def create_commit(
        self,
        title: str,
        note: str,
        consulted_files: list[str] | None = None
    ) -> Commit:
        """Create a versioning commit and index it semantically (asynchronously).

        1. Delegates to :meth:`Workspace.create_commit` (which detects diffs,
           stores blobs, and persists the commit JSON).
        2. Updates the co-occurrence graph.
        3. Pushes the commit to the background worker queue for semantic indexing.

        Args:
            title: Short commit title.
            note: Detailed Markdown note (the 'memory').
            consulted_files: Optional list of file paths consulted.

        Returns:
            The newly created :class:`~aivc.core.commit.Commit`.

        Raises:
            RuntimeError: if no changes detected and no files consulted.
        """
        # Step 1: core versioning (may raise RuntimeError if no changes)
        # Inject machine_id
        machine_id = get_machine_id()
        commit = self._workspace.create_commit(
            title, note, consulted_files=consulted_files, machine_id=machine_id
        )

        # Step 2: graph update (SQLite, always fast)
        self._graph.add_commit(commit)

        # Step 3: async semantic indexing
        self._index_queue.put(commit)

        # Step 4: Invalidate hints cache (new files might have been auto-tracked)
        self._local_hints_index = None

        return commit

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = 50,
        top_n: int = 5,
        filter_glob: str = "",
    ) -> list:
        """Semantic search over commit notes.

        Args:
            query: Free-text search query.
            top_k: Bi-Encoder recall breadth (capped at 50).
            top_n: Cross-Encoder reranked results to return.
            filter_glob: Optional glob pattern. If provided, restricts results
                         to commits that touch at least one matching file.

        Returns:
            A list of :class:`~aivc.semantic.searcher.SearchResult` sorted by
            relevance (descending).
        """
        if filter_glob:
            commit_ids = self._graph.get_commits_by_glob(filter_glob)
            if not commit_ids:
                return []
            return self._searcher.search(query, top_k=top_k, top_n=top_n, filter_ids=commit_ids)
        
        return self._searcher.search(query, top_k=top_k, top_n=top_n)

    def search_files_bm25(self, query: str, top_n: int = 5) -> list[dict]:
        """Perform a lexical search (BM25) on current tracked file contents.
        
        Args:
            query: The search query text.
            top_n: Number of results to return.
            
        Returns:
            A list of dicts: {"path": str, "score": float, "snippet": str}.
        """
        tracked_files = self.get_status()
        if not tracked_files:
            return []

        from rank_bm25 import BM25Okapi
        
        # 1. Get tokenized corpus from cache (handles I/O + regex caching)
        tracked_paths = [s.path for s in tracked_files]
        corpus, valid_paths = self._bm25_cache.get_corpus(tracked_paths)

        if not corpus:
            return []

        # 2. Memory-based BM25 score calculation
        bm25 = BM25Okapi(corpus)
        tokenized_query = self._bm25_cache.tokenize(query)
        scores = bm25.get_scores(tokenized_query)
        
        # 3. Identify top N candidates based on score
        candidates = []
        for path, score in zip(valid_paths, scores):
            if score > 0:
                candidates.append((path, float(score)))

        candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = candidates[:top_n]
        
        # 4. Build snippets ONLY for the top candidates (lazy I/O)
        import re
        query_words = set(tokenized_query)
        results = []

        for path, score in top_candidates:
            snippet = ""
            try:
                content = Path(path).read_text(encoding="utf-8", errors="ignore")
                matches = [m.start() for m in re.finditer(r'\w+', content) if m.group().lower() in query_words]
                
                if matches:
                    start = max(0, matches[0] - 100)
                    end = min(len(content), start + 200)
                    snippet = content[start:end].replace("\n", " ").strip()
                    if start > 0: snippet = "..." + snippet
                    if end < len(content): snippet = snippet + "..."
                else:
                    snippet = content[:200].replace("\n", " ").strip() + "..."
            except Exception:
                snippet = "[Error reading file]"

            results.append({
                "path": path,
                "score": score,
                "snippet": snippet
            })

        return results

    # ------------------------------------------------------------------
    # Graph queries
    # ------------------------------------------------------------------

    def get_related_files(
        self, file_path: str, top_n: int = 10
    ) -> list[tuple[str, int]]:
        """Return files frequently committed alongside *file_path*.

        Args:
            file_path: Relative path of the reference file.
            top_n: Maximum number of co-occurring files to return.

        Returns:
            List of ``(file_path, cooccurrence_count)`` sorted descending.
        """
        return self._graph.get_related_files(file_path, top_n=top_n)

    def get_commit_files(self, commit_id: str) -> list[str]:
        """Return file paths that were changed in a given commit."""
        return self._graph.get_commit_files(commit_id)

    def get_file_commits(self, file_path: str) -> list[str]:
        """Return commit IDs that have ever touched *file_path*."""
        return self._graph.get_file_commits(file_path)

    def graph_vis_data(self) -> dict:
        """Return the graph in visualisation format (nodes + edges)."""
        return self._graph.to_vis_data()

    def get_file_node_data(self) -> list[dict]:
        """Return enriched data for file nodes (dashboard vis)."""
        return self._graph.get_file_node_data()

    def get_file_cooccurrences(self) -> list[dict]:
        """Return weighted file-to-file co-occurrence edges (dashboard vis)."""
        return self._graph.get_file_cooccurrences()

    # ------------------------------------------------------------------
    # Workspace pass-throughs
    # ------------------------------------------------------------------

    def track(self, path: str, ignores: list[str] | None = None) -> dict[str, Any]:
        """Track a file, directory, or glob. See :meth:`Workspace.track`."""
        self._local_hints_index = None
        return self._workspace.track(path, ignores)

    def get_watched_dirs(self) -> dict[str, dict[str, Any]]:
        """Return exactly the watched directories state from workspace."""
        return self._workspace.get_watched_dirs()

    def untrack(self, path_or_glob: str) -> None:
        """Remove a file/dir from tracking. See :meth:`Workspace.untrack`."""
        self._local_hints_index = None
        self._workspace.untrack(path_or_glob)

    def get_status(self) -> list[FileStatus]:
        """Return status of all tracked files. See :meth:`Workspace.get_status`."""
        return self._workspace.get_status()

    def get_log(self, limit: int = 20, offset: int = 0) -> list[Commit]:
        """Return up to *limit* commits in reverse chronological order."""
        return self._workspace.get_log(limit, offset)

    def get_file_history(self, file_path: str) -> list[dict]:
        """Return commits that touched *file_path* with metadata.

        Returns:
            List of ``{"commit_id": str, "title": str, "timestamp": str}``
            sorted by timestamp descending.
        """
        return self._graph.get_file_commits_with_metadata(file_path)

    def get_commit(self, commit_id: str) -> Commit:
        """Load a single commit by ID."""
        return self._workspace.get_commit(commit_id)

    def find_child_commit(self, commit_id: str) -> Commit | None:
        """Find the commit that has *commit_id* as its parent."""
        return self._workspace.find_child_commit(commit_id)

    def read_file_at_commit(self, file_path: str, commit_id: str) -> bytes:
        """Read a tracked file as it was at a specific commit."""
        return self._workspace.read_file_at_commit(file_path, commit_id)
    
    def migrate_index(self) -> None:
        """Explicitly migrate JSON commits to SQLite index."""
        self._workspace.migrate_index()

    def _get_local_hints_index(self) -> dict[str, list[str]]:
        """Lazy-build an inverted index {basename: [paths]} for fast lookups."""
        if self._local_hints_index is None:
            index = {}
            # Use get_tracked_paths for O(1) path retrieval (no FileStatus overhead)
            for path_str in self._workspace.get_tracked_paths():
                basename = Path(path_str).name
                if basename not in index:
                    index[basename] = []
                index[basename].append(path_str)
            self._local_hints_index = index
        return self._local_hints_index

    def find_local_equivalent(self, remote_path: str, remote_blob_hash: str | None = None) -> str | None:
        """Try to find a local tracked file that matches a remote path.
        
        Optimised O(1) basename lookup.
        """
        remote_p = Path(remote_path)
        remote_basename = remote_p.name
        remote_parent_name = remote_p.parent.name if remote_p.parent else ""
        
        # O(1) lookup in inverted index
        candidates = self._get_local_hints_index().get(remote_basename, [])
        if not candidates:
            return None
        
        final_candidates = []
        for local_path in candidates:
            lp = Path(local_path)
            # 1. Check strong match via blob hash if available
            if remote_blob_hash:
                # _index is CoreIndex (SQLite) - this is still an I/O hit but 
                # only for files already matching the basename.
                local_blobs = self._workspace._index.get_blob_hashes_for_file(local_path)
                if remote_blob_hash in local_blobs:
                    return local_path
            
            # 2. Parent folder match (depth 1)
            local_parent_name = lp.parent.name if lp.parent else ""
            if local_parent_name == remote_parent_name:
                final_candidates.append(local_path)
        
        return final_candidates[0] if final_candidates else None

