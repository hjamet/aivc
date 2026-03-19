# AIVC — AI Version Control

**Serveur MCP de mémoire à long terme pour agents LLM**, inspiré du fonctionnement de la mémoire humaine et de Git.

> **État** : 🟢 Phase 14 terminée — Contexte de Commit (Prev/Next).

### Concept

AIVC transforme les **commits** en souvenirs pour un agent IA. Le système contourne la lourdeur de l'indexation sémantique de code brut :

1. L'agent consigne ses "achievements" en commits contenant une **note Markdown extrêmement détaillée** (le souvenir).
2. L'indexation sémantique (Bi-encoder + Cross-encoder) opère **exclusivement** sur ces notes.
3. Le recall fonctionne en entonnoir : `search_memory` (retourne des résumés) → `consult_commit` (retourne les détails/diffs), évitant la saturation de contexte.
4. L'historique des fichiers est conservé en stockage adressable par contenu (SHA-256).

---

## Installation

```bash
# Installation rapide (configure automatiquement le serveur MCP)
curl -fsSL https://raw.githubusercontent.com/hjamet/aivc/main/install.sh | bash

# OU installation locale depuis le repo
bash install.sh

# Installer uniquement le moteur core en mode développement
uv pip install -e ".[dev]"

# Lancer les tests
python -m pytest src/tests/ -v
```

**Pré-requis** : Python 3.11+, `uv` (`curl -fsSL https://astral.sh/uv/install.sh | sh`)
**Stack Phase 1** : stdlib uniquement (`hashlib`, `uuid`, `json`, `pathlib`)
**Stack Phase 2** : ChromaDB, SentenceTransformers (`all-MiniLM-L6-v2`), Cross-Encoder (`ms-marco-MiniLM-L-6-v2`).
**Stack Phase 3** : MCP Python SDK (`mcp>=1.0`), FastMCP (transport stdio).

---

## Description Détaillée

### Coeur — Moteur de Versioning (Phase 1)

Stockage adressable par contenu SHA-256, inspiré de Git :

- **BlobStore** : stocke des blobs binaires immuables, dédupliqués par hash. Reference Counting intégré — un blob est supprimé physiquement seulement quand plus aucun fichier ne le référence (Garbage Collection).
- **Commit** : unité atomique de mémoire. Titre court + note Markdown détaillée + liste des `FileChange` avec impact de taille (`+X B / -Y B`).
- **Diff** : compare l'état connu (dernier hash) au disque actuel — détecte `added`, `modified`, `deleted`.
- **Workspace** : orchestrateur. Track des fichiers/dossiers/globs, crée des commits, calcule le statut (taille courante + historique), gère l'untrack avec GC.

### Flux

```
track(path/glob/dir) --> workspace.json
    | create_commit(title, note)
    --> compute_diff() --> BlobStore.store() --> Commit.json
    | untrack(file)
    --> BlobStore.decrement_ref() --> GC si refcount=0
```

### Outils MCP Exposés (Phase 3)

| Outil | Type | Description |
|-------|------|-------------|
| `create_commit` | Écriture | Mémorise un accomplissement (Titre + Détails Markdown) et snapshots les fichiers. **Appeler souvent — après chaque étape.** |
| `search_memory` | Lecture | Recherche sémantique. Retourne Top Commits (ID, titre, score) + fichiers les plus fréquents. Supporte un filtre glob optionnel. |
| `get_recent_commits`| Lecture | Journal des N derniers commits (paginable par offset/limit), façon `git log`. |
| `consult_commit`| Lecture | Contenu complet (note Markdown + FileChange) d'un commit spécifique. |
| `consult_file` | Lecture | Historique AIVC d'un fichier : liste des commits qui l'ont touché. |
| `get_status` | Lecture | Fichiers suivis avec taille courante et poids de l'historique. |
| `untrack` | Gestion | ⚠️ DESTRUCTIF — Retire un fichier et supprime son historique (GC). |
| `track` | Gestion | Ajouter un fichier, dossier ou glob au suivi AIVC. |
| `read_historical_file` | Lecture | Contenu d'un fichier tel qu'il était lors d'un commit passé. |

---

## Documentation Index

| Titre | Description |
|-------|-------------|
| [Index Architecture](docs/index_architecture.md) | Architecture technique du projet |
| [Index Tâches](docs/index_tasks.md) | Spécifications des tâches de la roadmap |

---

## Plan du Repo

```
aivc/
├── .agent/
├── docs/
│   ├── tasks/
│   │   ├── phase1_versioning_engine.md
│   │   ├── phase2_semantic_graph.md
│   │   ├── phase3_mcp_interface.md
│   │   ├── phase6_absolute_paths_fix.md
│   │   └── phase9_cli_exposure.md
│   ├── index_architecture.md
│   └── index_tasks.md
├── scripts/
│   └── migrate_commit_paths.py  # Migration one-shot chemins relatifs → absolus
├── src/
│   ├── aivc/
│   │   ├── __init__.py
│   │   ├── server.py             # Serveur MCP (Phase 3) — 9 outils FastMCP
│   │   ├── cli.py                # CLI (aivc status/track/log/search/web)
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── blob_store.py    # SHA-256 + Refcount/GC
│   │   │   ├── commit.py        # Dataclasses Commit + FileChange
│   │   │   ├── diff.py          # Détection des changements
│   │   │   └── workspace.py     # Orchestrateur Phase 1
│   │   ├── semantic/
│   │   │   ├── __init__.py
│   │   │   ├── indexer.py       # ChromaDB + SentenceTransformer
│   │   │   ├── searcher.py      # Pipeline Bi-Encoder → Cross-Encoder
│   │   │   ├── graph.py         # Graphe bipartite fichiers↔commits
│   │   │   └── engine.py        # Façade SemanticEngine (Phase 2)
│   │   └── web/
│   │       └── dashboard.py     # Web Dashboard Cytoscape.js
│   └── tests/
│       ├── conftest.py           # Marker requires_ml + --run-ml flag
│       ├── test_blob_store.py
│       ├── test_commit.py
│       ├── test_diff.py
│       ├── test_workspace.py
│       ├── test_migrate.py      # Phase 6
│       ├── test_cli.py          # Phase 4 + 6
│       ├── test_indexer.py      # Phase 2
│       ├── test_searcher.py     # Phase 2
│       ├── test_graph.py        # Phase 2
│       ├── test_engine.py       # Phase 2
│       └── test_server.py       # Phase 3 — mock SemanticEngine
├── install.sh                   # Installation + config MCP automatique
├── pyproject.toml
├── .gitignore
└── README.md
```

---

## Scripts d'Entrée Principaux

| Commande | Description |
|----------|-------------|
| `aivc status` | Afficher les fichiers suivis et leur poids |
| `aivc track <path>` | Ajouter un fichier/dossier/glob au tracking |
| `aivc log [-n N]` | Afficher l'historique des commits |
| `aivc search <query> [-g GLOB]` | Recherche sémantique dans la mémoire, avec filtre optionnel |
| `aivc web [-p PORT]` | Lancer le Web Dashboard interactif |
| `python -m pytest src/tests/ -v` | Lancer la suite de tests complète |
| `uv pip install -e ".[dev]"` | Installer uniquement le core (stdlib) |
| `uv pip install -e ".[semantic]"` | Installer avec les dépendances IA (Phase 2) |

---

## Scripts Exécutables Secondaires & Utilitaires

| `bash install.sh` | Installer AIVC (prod ~/.aivc) et configurer le serveur MCP |
| `bash install_dev.sh` | Installer AIVC (dev local .venv) pour tester avec le code local |
| `python -m aivc.web.dashboard` | Lancer le Web Dashboard (graphe interactif sur le port 8765) |
| `python scripts/migrate_commit_paths.py` | Migration one-shot des chemins relatifs → absolus (Phase 6) |

---

## Roadmap

| Phase | Nom | Spec | État |
|-------|-----|------|------|
| **1** | [Moteur de Versioning Interne (Core)](docs/tasks/phase1_versioning_engine.md) | Blobs SHA-256, Garbage Collection | 🟢 Terminé |
| **2** | [Moteur Sémantique et Graphe](docs/tasks/phase2_semantic_graph.md) | Bi/Cross Encoder, ChromaDB, install.sh MCP | 🟢 Terminé |
| **3** | [Interface MCP et Outils](docs/tasks/phase3_mcp_interface.md) | Entonnoir Recall, 8 outils, prompt système | 🟢 Terminé |
| **4** | [Interface CLI & Web Dashboard](docs/tasks/phase4_cli_and_dashboard.md) | Outils terminaux (`aivc`), Graphe interactif (Taille/Couleur) avec recherche sémantique ciblée | 🟢 Terminé |
| **5** | [Stabilisation MVP & Bugfixes](docs/tasks/phase5_stabilization.md) | Chemins absolus, autodiscovery de port, vendoring de Cytoscape | 🟢 Terminé |
| **6** | [Consolidation Absolue & CLI](docs/tasks/phase6_absolute_paths_fix.md) | Assainir l'historique vers l'absolu 100%, ajouter `aivc track` | 🟢 Terminé |
| **7** | [Scoped Semantic Search](docs/tasks/phase7_scoped_search.md) | Filtrage par glob dans `search_memory` (MCP + CLI) | 🟢 Terminé |
| **8** | [Injection GEMINI.md](docs/tasks/phase8_gemini_injection.md) | Bonnes pratiques agent injectées via `install.sh` | 🟢 Terminé |
| **9** | [Exposition CLI](docs/tasks/phase9_cli_exposure.md) | Symlink automatique vers `~/.local/bin/aivc` | 🟢 Terminé |
| **10** | [Search Result Snippets](docs/tasks/phase10_search_snippets.md) | Extraits contextuels dans les résultats `search_memory` | 🟡 À faire |
| **11** | [Track MCP Tool](docs/tasks/phase11_track_mcp_tool.md) | Exposition de l'outil `track` dans le serveur MCP | 🟢 Terminé |
| **12** | [Fichiers Consultés](docs/tasks/phase12_consulted_files.md) | Action `consulted` dans les commits, enrichissement graphe | 🟡 À faire |
| **13** | [Recherche BM25 Fichiers](docs/tasks/phase13_bm25_file_search.md) | Recherche lexicale BM25 sur contenu des fichiers traqués | 🟡 À faire |
| **14** | [Contexte de Commit](docs/tasks/phase14_commit_context.md) | Affichage du commit Parent/Enfant dans `consult_commit` | 🟢 Terminé |
| **15** | [Refactoring Performance I/O](docs/tasks/phase15_io_refactoring.md) | Élimination de `_all_commits()`, migration vers SQLite | 🟡 À faire |

### Documentation Index
| Titre (Lien) | Description |
|--------------|-------------|
| [Spec Phase 6](docs/tasks/phase6_absolute_paths_fix.md) | Spécification technique pour finaliser l'absolu. |
| [Spec Phase 7](docs/tasks/phase7_scoped_search.md) | Filtrage sémantique par glob. |
| [Spec Phase 8](docs/tasks/phase8_gemini_injection.md) | Injection bonnes pratiques agent dans GEMINI.md. |
| [Spec Phase 9](docs/tasks/phase9_cli_exposure.md) | Création d'un lien symbolique pour l'accès global à la commande CLI. |
| [Spec Phase 10](docs/tasks/phase10_search_snippets.md) | Extraits contextuels dans les résultats de recherche sémantique. |
| [Spec Phase 11](docs/tasks/phase11_track_mcp_tool.md) | Exposition de l'outil `track` dans le serveur MCP. |
| [Spec Phase 12](docs/tasks/phase12_consulted_files.md) | Action `consulted` dans les commits. |
| [Spec Phase 13](docs/tasks/phase13_bm25_file_search.md) | Recherche BM25 sur fichiers traqués. |
| [Spec Phase 14](docs/tasks/phase14_commit_context.md) | Graphe chronologique de commits. |
| [Spec Phase 15](docs/tasks/phase15_io_refactoring.md) | Refactoring performance I/O. |
