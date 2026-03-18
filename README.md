# AIVC — AI Version Control

**Serveur MCP de mémoire à long terme pour agents LLM**, inspiré du fonctionnement de la mémoire humaine et de Git.

> **État** : 🟡 Phase 1 implémentée — Moteur de versioning interne opérationnel. Phase 2 (sémantique) à venir.

### Concept

AIVC transforme les **commits** en souvenirs pour un agent IA. Le système contourne la lourdeur de l'indexation sémantique de code brut :

1. L'agent consigne ses "achievements" en commits contenant une **note Markdown extrêmement détaillée** (le souvenir).
2. L'indexation sémantique (Bi-encoder + Cross-encoder) opère **exclusivement** sur ces notes.
3. Le recall fonctionne en entonnoir : `search_memory` (retourne des résumés) → `consult_commit` (retourne les détails/diffs), évitant la saturation de contexte.
4. L'historique des fichiers est conservé en stockage adressable par contenu (SHA-256).

---

## Installation

```bash
# Installer le moteur core en mode développement
pip install -e ".[dev]"

# Lancer les tests
python -m pytest src/tests/ -v
```

**Pré-requis** : Python 3.11+
**Stack Phase 1** : stdlib uniquement (`hashlib`, `uuid`, `json`, `pathlib`)
**Stack Phase 2+** : ChromaDB, SentenceTransformers (`all-MiniLM-L6-v2`), Cross-Encoder.

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
| `create_commit` | Écriture | Mémorise un événement (Titre + Détails Markdown) et snapshot les fichiers. |
| `search_memory` | Lecture | Recherche intelligente. Retourne Top Commits/Fichiers (titres uniquement). |
| `consult_commit`| Lecture | Plonge dans un commit spécifique pour voir le message complet et les diffs. |
| `get_status` | Lecture | Liste les fichiers surveillés, avec leur taille courante et la taille de leur historique. |
| `untrack` | Gestion | Retire un fichier de la surveillance ET supprime son historique (Garbage Collected). |
| `read_historical_file` | Lecture | Consulte une version passée d'un fichier. |

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
│   │   └── core/
│   │       ├── __init__.py
│   │       ├── blob_store.py    # SHA-256 + Refcount/GC
│   │       ├── commit.py        # Dataclasses Commit + FileChange
│   │       ├── diff.py          # Détection des changements
│   │       └── workspace.py     # Orchestrateur principal
│   └── tests/
│       ├── test_blob_store.py
│       ├── test_commit.py
│       ├── test_diff.py
│       └── test_workspace.py
├── pyproject.toml
├── .gitignore
└── README.md
```

---

## Scripts d'Entrée Principaux

| Commande | Description |
|----------|-------------|
| `python -m pytest src/tests/ -v` | Lancer la suite de tests (48 tests) |
| `pip install -e ".[dev]"` | Installer le package en mode développement |

---

## Scripts Exécutables Secondaires & Utilitaires

> Aucun -- interface MCP en Phase 3.

---

## Roadmap

| Phase | Nom | Spec | État |
|-------|-----|------|------|
| **1** | [Moteur de Versioning Interne (Core)](docs/tasks/phase1_versioning_engine.md) | Blobs SHA-256, Garbage Collection | 🟢 Terminé |
| **2** | [Moteur Sémantique et Graphe](docs/tasks/phase2_semantic_graph.md) | Bi/Cross Encoder, ChromaDB, UI | 🔴 À faire |
| **3** | [Interface MCP et Outils](docs/tasks/phase3_mcp_interface.md) | Entonnoir Recall, Untrack destructif | 🔴 À faire |
