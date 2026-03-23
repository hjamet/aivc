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

from __future__ import annotations

from pathlib import Path

from aivc.core.commit import Commit
from aivc.core.workspace import FileStatus, Workspace
from aivc.semantic.graph import CooccurrenceGraph


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
        """Create a versioning commit and index it semantically.

        1. Delegates to :meth:`Workspace.create_commit` (which detects diffs,
           stores blobs, and persists the commit JSON).
        2. Indexes the commit note in ChromaDB.
        3. Updates the co-occurrence graph.

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
        commit = self._workspace.create_commit(title, note, consulted_files=consulted_files)

        # Step 2: semantic indexing — triggers lazy load on first call
        self._indexer.index_commit(commit)

        # Step 3: graph update (SQLite, always fast)
        self._graph.add_commit(commit)

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
        return self._workspace.track(path, ignores)

    def get_watched_dirs(self) -> dict[str, dict[str, Any]]:
        """Return exactly the watched directories state from workspace."""
        return self._workspace.get_watched_dirs()

    def untrack(self, path_or_glob: str) -> None:
        """Remove a file/dir from tracking. See :meth:`Workspace.untrack`."""
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

