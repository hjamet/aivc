"""
AIVC Semantic Layer — Phase 2.

Provides vector indexing, semantic search, and co-occurrence graph for commits.
Heavy dependencies (sentence-transformers, chromadb) are only imported when
their respective classes are actually used — not at package import time.
"""

# Expose the public API. Individual submodules can be imported directly
# (e.g. ``from aivc.semantic.graph import CooccurrenceGraph``) without
# triggering the heavy ML dependencies.

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Type-checkers get the full imports; runtime avoids cascading heavy deps.
    from aivc.semantic.indexer import Indexer
    from aivc.semantic.searcher import SearchResult, Searcher
    from aivc.semantic.graph import CooccurrenceGraph
    from aivc.semantic.engine import SemanticEngine

__all__ = [
    "Indexer",
    "Searcher",
    "SearchResult",
    "CooccurrenceGraph",
    "SemanticEngine",
]

