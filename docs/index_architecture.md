# Index Architecture

| Titre de la note | Courte Description | Dernière modif | Tag |
|------------------|-------------------|----------------|-----|
| [Phase 1 — Core Versioning Engine](../src/aivc/core/blob_store.py) | BlobStore SHA-256 + Refcount/GC | 2026-03-18 | `Up to date` |
| [Phase 1 — Commit Structure](../src/aivc/core/commit.py) | Dataclasses Commit & FileChange avec impact taille | 2026-03-18 | `Up to date` |
| [Phase 1 — Diff Engine](../src/aivc/core/diff.py) | Détection added/modified/deleted | 2026-03-18 | `Up to date` |
| [Phase 1 — Workspace Orchestrator](../src/aivc/core/workspace.py) | Track glob/dir, GC, status, log | 2026-03-18 | `Up to date` |
| [Phase 2 — Indexer ChromaDB](../src/aivc/semantic/indexer.py) | Vectorisation des notes commits + upsert ChromaDB | 2026-03-18 | `Up to date` |
| [Phase 2 — Searcher Bi/Cross-Encoder](../src/aivc/semantic/searcher.py) | Pipeline Bi-Encoder → Cross-Encoder, SearchResult | 2026-03-18 | `Up to date` |
| [Phase 2 — CooccurrenceGraph](../src/aivc/semantic/graph.py) | Graphe bipartite fichiers↔commits, export vis | 2026-03-18 | `Up to date` |
| [Phase 2 — SemanticEngine](../src/aivc/semantic/engine.py) | Façade orchestrant Workspace + Indexer + Graph + Searcher | 2026-03-18 | `Up to date` |
| [Phase 17 — Watchdog Daemon](../src/aivc/server.py) | Surveillance temps réel + Sync au démarrage | 2026-03-19 | `Up to date` |
| [Phase 17 — Watched Dirs Management](../src/aivc/core/workspace.py) | Gestion de l'état `watched_dirs` et filtrage des fichiers cachés | 2026-03-19 | `Up to date` |
