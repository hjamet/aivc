# Phase 15 — Refactoring Performance I/O (CoreIndex)

## 1. Contexte & Discussion (Narratif)
Lors de la revue d'architecture du 19 mars 2026, l'Architecte a identifié un goulet d'étranglement critique dans `Workspace._all_commits()`. Cette fonction charge **tous les fichiers JSON** du dossier `commits/` à chaque appel à `get_status()` ou `untrack()`. Sur un historique de plusieurs centaines de commits, cela génère un nombre prohibitif d'accès disque et de parsing JSON.

Deux options architecturales ont été proposées :
- **Option A** : Remonter la logique dans `SemanticEngine` (faire de l'engine le chef d'orchestre des requêtes performantes).
- **Option B** : Créer un `CoreIndex` SQLite autonome dans `core/` pour que `Workspace` devienne ultra-rapide par lui-même, sans dépendance vers la couche sémantique.

**L'utilisateur a validé l'Option B** le 19 mars 2026. La raison principale : préserver l'isolation stricte entre le moteur de versioning (`core/`) et la couche sémantique (`semantic/`). Le `CoreIndex` est un composant léger, stdlib-compatible (SQLite est dans la stdlib Python), qui stocke de la métadonnée rapide (commit ID, parent_id, chemins de fichiers, hashes de blobs).

Le `CooccurrenceGraph` existant dans `semantic/graph.py` perdure mais se concentre exclusivement sur la recherche sémantique (co-occurrence fichiers↔commits, requêtes par glob).

## 2. Fichiers Concernés
- `src/aivc/core/index.py` — **[NOUVEAU]** CoreIndex SQLite : table `commits` (id, parent_id, timestamp, title), table `file_changes` (commit_id, path, blob_hash, action, bytes_added, bytes_removed)
- `src/aivc/core/workspace.py` — Intègre le `CoreIndex`, supprime `_all_commits()`, optimise `get_status()`, `untrack()`, `find_child_commit()`
- `src/aivc/semantic/engine.py` — Aucun changement structurel attendu (les pass-throughs restent identiques)
- `src/tests/test_index.py` — **[NOUVEAU]** Tests unitaires du CoreIndex
- `src/tests/test_workspace.py` — Vérification de la non-régression
- `src/tests/test_server.py` — Vérification que les outils MCP restent fonctionnels

## 3. Objectifs (Definition of Done)
* Un fichier `src/aivc/core/index.py` existe, contenant un `CoreIndex` SQLite avec les tables `commits` et `file_changes`.
* `Workspace` possède et alimente ce `CoreIndex` à chaque `create_commit()`.
* Au premier lancement, les commits JSON existants sont migrés automatiquement vers le `CoreIndex`.
* `Workspace.get_status()` n'appelle plus `_all_commits()` mais requête le `CoreIndex`.
* `Workspace.untrack()` n'appelle plus `_all_commits()` mais requête le `CoreIndex`.
* `Workspace.find_child_commit()` utilise le `CoreIndex` pour un lookup O(1) au lieu de traverser toute la chaîne.
* `_all_commits()` est supprimé ou déprécié.
* Aucune régression sur les tests existants.
* Aucune dépendance de `core/` vers `semantic/` n'est introduite.
