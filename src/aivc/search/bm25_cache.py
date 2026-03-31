"""
BM25Cache: Persistent cache for BM25 tokenization.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple


class BM25Cache:
    """Caches tokenized file contents to avoid redundant I/O and Regex.
    
    Stores data in a SQLite database under storage_root/bm25_cache.db.
    """

    def __init__(self, storage_root: Path) -> None:
        self._storage_root = storage_root
        self._db_path = storage_root / "bm25_cache.db"
        self._init_db()

    def _init_db(self) -> None:
        self._storage_root.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_cache (
                    path TEXT PRIMARY KEY,
                    mtime REAL,
                    size INTEGER,
                    tokens_json TEXT
                )
            """)
            conn.commit()

    def tokenize(self, text: str) -> List[str]:
        """Simple regex-based tokenization (lowercase, words)."""
        return re.findall(r'\w+', text.lower())

    def get_corpus(
        self, 
        tracked_paths: List[str], 
        metadata: Dict[str, Dict[str, Any]] | None = None
    ) -> Tuple[List[List[str]], List[str]]:
        """Retrieve or compute tokens for the given tracked files.
        
        Args:
            tracked_paths: List of absolute paths to tracked files.
            metadata: Optional dict of {path: {"mtime": float, "size": int}} 
                      from workspace state. If provided, skips disk stat syscalls.
            
        Returns:
            A tuple (list of token lists, list of available paths).
        """
        corpus = []
        valid_paths = []
        
        # Use provided metadata to avoid 1000s of disk stats (especially on WSL)
        direct_metadata = metadata if metadata is not None else {}
        
        with sqlite3.connect(self._db_path) as conn:
            # Load existing cache in one go
            cursor = conn.execute("SELECT path, mtime, size, tokens_json FROM file_cache")
            cache = {row[0]: (row[1], row[2], row[3]) for row in cursor.fetchall()}
            
            new_cache_entries = []
            
            for abs_path in tracked_paths:
                p = Path(abs_path)
                
                try:
                    # Get stats from memory/AIVC state if available, else hit disk ONCE
                    meta = direct_metadata.get(abs_path)
                    if meta:
                        mtime = meta.get("mtime", 0.0)
                        size = meta.get("size", 0)
                    else:
                        # Fallback for untracked files or manual calls
                        if not (p.exists() and p.is_file()):
                            continue
                        stat = p.stat()
                        mtime = stat.st_mtime
                        size = stat.st_size
                    
                    cached = cache.get(abs_path)
                    if cached and cached[0] == mtime and cached[1] == size:
                        # Cache hit
                        tokens = json.loads(cached[2])
                    else:
                        # Cache miss (file changed or not in cache)
                        # We still need one disk read here to get new content
                        content = p.read_text(encoding="utf-8", errors="ignore")
                        tokens = self.tokenize(content)
                        new_cache_entries.append((abs_path, mtime, size, json.dumps(tokens)))
                    
                    corpus.append(tokens)
                    valid_paths.append(abs_path)
                except Exception:
                    continue

            # Update cache for modified/new files
            if new_cache_entries:
                conn.executemany(
                    "INSERT OR REPLACE INTO file_cache (path, mtime, size, tokens_json) VALUES (?, ?, ?, ?)",
                    new_cache_entries
                )
                conn.commit()
                
            # Cleanup orphaned entries (files no longer tracked)
            # Optional: for performance, only do this occasionally
            tracked_set = set(tracked_paths)
            orphans = [p for p in cache if p not in tracked_set]
            if orphans:
                conn.executemany("DELETE FROM file_cache WHERE path = ?", [(p,) for p in orphans])
                conn.commit()

        return corpus, valid_paths
