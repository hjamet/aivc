# AIVC — AI Version Control

**Serveur MCP de mémoire à long terme pour agents LLM**, inspiré du fonctionnement de la mémoire humaine et de Git.

> **État** : 🟢 Phase 3 terminée — Interface MCP complète (8 outils, prompt système, entonnoir de recall).

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
| `search_memory` | Lecture | Recherche sémantique. Retourne Top Commits (ID, titre, score) + fichiers les plus fréquents. |
| `get_recent_commits`| Lecture | Journal des N derniers commits (paginable par offset/limit), façon `git log`. |
| `consult_commit`| Lecture | Contenu complet (note Markdown + FileChange) d'un commit spécifique. |
| `consult_file` | Lecture | Historique AIVC d'un fichier : liste des commits qui l'ont touché. |
| `get_status` | Lecture | Fichiers suivis avec taille courante et poids de l'historique. |
| `untrack` | Gestion | ⚠️ DESTRUCTIF — Retire un fichier et supprime son historique (GC). |
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
│   │   └── phase3_mcp_interface.md
│   ├── index_architecture.md
│   └── index_tasks.md
├── src/
│   ├── aivc/
│   │   ├── __init__.py
│   │   ├── server.py             # Serveur MCP (Phase 3) — 8 outils FastMCP
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── blob_store.py    # SHA-256 + Refcount/GC
│   │   │   ├── commit.py        # Dataclasses Commit + FileChange
│   │   │   ├── diff.py          # Détection des changements
│   │   │   └── workspace.py     # Orchestrateur Phase 1
│   │   └── semantic/
│   │       ├── __init__.py
│   │       ├── indexer.py       # ChromaDB + SentenceTransformer
│   │       ├── searcher.py      # Pipeline Bi-Encoder → Cross-Encoder
│   │       ├── graph.py         # Graphe bipartite fichiers↔commits
│   │       └── engine.py        # Façade SemanticEngine (Phase 2)
│   └── tests/
│       ├── conftest.py           # Marker requires_ml + --run-ml flag
│       ├── test_blob_store.py
│       ├── test_commit.py
│       ├── test_diff.py
│       ├── test_workspace.py
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
| `bash install.sh` | Installer AIVC et configurer le serveur MCP |
| `python -m pytest src/tests/ -v` | Lancer la suite de tests complète |
| `uv pip install -e ".[dev]"` | Installer uniquement le core (stdlib) |
| `uv pip install -e ".[semantic]"` | Installer avec les dépendances IA (Phase 2) |

---

## Scripts Exécutables Secondaires & Utilitaires

> Aucun -- interface MCP en Phase 3.

---

## Roadmap

| Phase | Nom | Spec | État |
|-------|-----|------|------|
| **1** | [Moteur de Versioning Interne (Core)](docs/tasks/phase1_versioning_engine.md) | Blobs SHA-256, Garbage Collection | 🟢 Terminé |
| **2** | [Moteur Sémantique et Graphe](docs/tasks/phase2_semantic_graph.md) | Bi/Cross Encoder, ChromaDB, install.sh MCP | 🟢 Terminé |
| **3** | [Interface MCP et Outils](docs/tasks/phase3_mcp_interface.md) | Entonnoir Recall, 8 outils, prompt système | 🟢 Terminé |
| **4** | [Interface CLI & Web Dashboard](docs/tasks/phase4_cli_and_dashboard.md) | Outils terminaux (`aivc`), Graphe interactif (Taille/Couleur) avec recherche sémantique ciblée | 🔴 À faire |
