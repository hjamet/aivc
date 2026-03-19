# Phase 15 — Refactoring Performance I/O

## 1. Contexte & Discussion (Narratif)
Lors de la revue d'architecture du 19 mars 2026, l'Architecte a identifié un goulet d'étranglement critique dans `Workspace._all_commits()`. Cette fonction charge **tous les fichiers JSON** du dossier `commits/` à chaque appel à `get_status()` ou `untrack()`. Sur un historique de plusieurs centaines de commits, cela génère un nombre prohibitif d'accès disque et de parsing JSON.

La solution retenue : exploiter le `CooccurrenceGraph` existant (SQLite, déjà rapide) en y ajoutant le champ `parent_id` dans la table `commit_nodes`. Cela permettra de répondre aux requêtes relationnelles (parent, enfant, fichiers associés) sans charger les JSON individuels, et d'éliminer progressivement `_all_commits()`.

L'utilisateur a approuvé cette proposition à 100%.

## 2. Fichiers Concernés
- `src/aivc/semantic/graph.py` — Ajout de `parent_id` au schéma SQL `commit_nodes`, migration du schéma existant
- `src/aivc/core/workspace.py` — Remplacement progressif de `_all_commits()` par des requêtes SQLite via le graph
- `src/aivc/semantic/engine.py` — Éventuelle nouvelle méthode exposant les relations parent/enfant
- `src/tests/test_graph.py` — Tests des nouvelles requêtes SQL
- `src/tests/test_server.py` — Vérification que les outils MCP restent fonctionnels

## 3. Objectifs (Definition of Done)
* La table `commit_nodes` du `CooccurrenceGraph` contient un champ `parent_id` indexé.
* Les commits existants sont migrés automatiquement au premier lancement (lecture du JSON → insertion du parent_id en SQL).
* `Workspace.get_status()` n'appelle plus `_all_commits()` mais utilise le graphe SQLite.
* `Workspace.untrack()` n'appelle plus `_all_commits()` mais utilise le graphe SQLite.
* Aucune régression sur les tests existants.
