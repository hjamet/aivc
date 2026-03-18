# AIVC — AI Version Control

**Serveur MCP de mémoire à long terme pour agents LLM**, inspiré du fonctionnement de la mémoire humaine et de Git.

> **État** : 🔴 Phase de conception — Aucun code implémenté.

### Concept

AIVC transforme les **commits** en souvenirs pour un agent IA. Le système contourne la lourdeur de l'indexation sémantique de code brut :

1. L'agent consigne ses "achievements" en commits contenant une **note Markdown extrêmement détaillée** (le souvenir).
2. L'indexation sémantique (Bi-encoder + Cross-encoder) opère **exclusivement** sur ces notes.
3. Le recall fonctionne en entonnoir : `search_memory` (retourne des résumés) → `consult_commit` (retourne les détails/diffs), évitant la saturation de contexte.
4. L'historique des fichiers est conservé en stockage adressable par contenu (SHA-256).

---

## Installation

> ⚠️ Pas encore disponible — en cours de conception.

Le serveur sera installé de manière isolée pour éviter de polluer l'environnement système :
```bash
# L'installation créera un venv dédié dans ~/.aivc/
bash install.sh
```

**Pré-requis** : Python 3.11+
**Stack** : ChromaDB, SentenceTransformers (`all-MiniLM-L6-v2`), Cross-Encoder.

---

## Fonctionnalités Clés

### Outils MCP Exposés

| Outil | Type | Description |
|-------|------|-------------|
| `create_commit` | Écriture | Mémorise un événement (Titre + Détails Markdown) et snapshot les fichiers. |
| `search_memory` | Lecture | Recherche intelligente. Retourne Top Commits/Fichiers (titres uniquement). |
| `consult_commit`| Lecture | Plonge dans un commit spécifique pour voir le message complet et les diffs. |
| `get_status` | Lecture | Liste les fichiers surveillés, avec leur taille courante et la taille de leur historique. |
| `untrack` | Gestion | Retire un fichier de la surveillance ET supprime son historique (Garbage Collected). |
| `read_historical_file` | Lecture | Consulte une version passée d'un fichier. |

### Interface Visuelle (Graphe)

Le système inclut une interface web locale facultative permettant de visualiser le **graphe de co-occurrence** (liens entre fichiers et commits).

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
│   └── aivc/
│       ├── core/              # Moteur de versioning (SHA-256, GC)
│       ├── semantic/          # Base vectorielle, Bi/Cross Encoder
│       ├── tools/             # Outils MCP
│       └── ui/                # Serveur de visualisation (Graphe)
├── .gitignore
└── README.md
```

---

## Scripts d'Entrée Principaux

> Aucun script — projet en phase de conception.

---

## Scripts Exécutables Secondaires & Utilitaires

> Aucun — projet en phase de conception.

---

## Roadmap

| Phase | Nom | Spec | État |
|-------|-----|------|------|
| **1** | [Moteur de Versioning Interne (Core)](docs/tasks/phase1_versioning_engine.md) | Blobs SHA-256, Garbage Collection | 🔴 À faire |
| **2** | [Moteur Sémantique et Graphe](docs/tasks/phase2_semantic_graph.md) | Bi/Cross Encoder, ChromaDB, UI | 🔴 À faire |
| **3** | [Interface MCP et Outils](docs/tasks/phase3_mcp_interface.md) | Entonnoir Recall, Untrack destructif | 🔴 À faire |
