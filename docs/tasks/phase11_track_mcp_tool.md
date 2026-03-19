# Phase 11 — Exposer l'outil `track` dans le serveur MCP

## 1. Contexte & Discussion (Narratif)

Lors de la session d'architecture du 19 mars 2026, on a constaté que l'outil `track` est la **seule opération de gestion** qui n'est pas exposée dans le serveur MCP. C'est une omission : le code existe dans `Workspace.track()`, est wrappé dans `SemanticEngine.track()`, et est accessible via le CLI (`aivc track`), mais n'apparaît simplement pas dans `server.py`.

Sans cet outil, l'agent LLM ne peut pas ajouter de nouveaux fichiers au suivi via MCP. Il dépend du CLI ou d'un tracking manuel, ce qui casse le workflow autonome de l'agent.

L'outil `untrack` est exposé, ce qui rend l'absence de `track` encore plus incohérente.

## 2. Fichiers Concernés

- `src/aivc/server.py` — Ajout de l'outil MCP `track`
- `src/aivc/server.py` — Mise à jour du `_SYSTEM_PROMPT` (table des outils)
- `src/tests/test_server.py` — Tests unitaires pour le nouvel outil

## 3. Objectifs (Definition of Done)

* L'outil MCP `track(path)` est exposé dans `server.py` via `@mcp.tool()`.
* Il accepte un chemin (fichier, dossier, ou glob pattern).
* Il retourne la liste des fichiers nouvellement traqués, ou un message indiquant qu'aucun nouveau fichier n'a été ajouté.
* Le `_SYSTEM_PROMPT` dans `server.py` est mis à jour pour inclure `track` dans la table des outils.
* La table des outils MCP dans le README est mise à jour.
* Des tests unitaires couvrent les cas : tracking réussi, tracking d'un fichier déjà suivi, pattern invalide.
