# Phase 12 — Fichiers "Consultés" dans les Commits

## 1. Contexte & Discussion (Narratif)

Lors de la session d'architecture du 19 mars 2026, l'utilisateur a proposé d'enrichir le modèle de données des commits pour permettre à l'agent d'associer des fichiers **non modifiés** à un commit, en mode "consultation".

L'idée : quand un agent travaille sur une tâche, il consulte souvent des fichiers de référence sans les modifier. Ces fichiers fournissent du contexte crucial mais ne sont pas enregistrés dans le commit. Résultat : le graphe de co-occurrence perd de l'information et les requêtes `get_related_files` sont moins pertinentes.

### Insistance de l'utilisateur

L'utilisateur a **fortement insisté** sur la qualité de la documentation de ce paramètre dans le prompt système. Le modèle doit comprendre qu'il ne doit mentionner **que les documents qui lui ont été VÉRITABLEMENT utiles** — pas une utilité de surface, mais des documents contenant des informations que l'agent **ne connaissait pas avant de les avoir lus**.

### Décisions techniques

- Les fichiers consultés ont l'action `consulted` dans `FileChange`.
- **Aucun blob** n'est stocké (pas de snapshot du contenu).
- **Aucun refcount** n'est modifié.
- Le graphe de co-occurrence enregistre normalement les edges fichier↔commit.
- Les fichiers consultés **doivent être traqués** pour être mentionnés.
- Le paramètre `consulted_files` de `create_commit` est optionnel (liste vide par défaut).

## 2. Fichiers Concernés

- `src/aivc/core/commit.py` — Ajouter `consulted` aux actions valides de `FileChange`
- `src/aivc/core/workspace.py` — Accepter `consulted_files` dans `create_commit()`
- `src/aivc/semantic/engine.py` — Pass-through du paramètre
- `src/aivc/server.py` — Ajouter le paramètre à l'outil MCP `create_commit`
- `src/aivc/server.py` — Mise à jour du `_SYSTEM_PROMPT` pour documenter le comportement
- `src/tests/test_commit.py` — Tests de la nouvelle action
- `src/tests/test_workspace.py` — Tests de `create_commit` avec fichiers consultés

## 3. Objectifs (Definition of Done)

* `FileChange` accepte `action="consulted"` avec `blob_hash=None`, `bytes_added=0`, `bytes_removed=0`.
* `create_commit(title, note, consulted_files=[...])` ajoute les fichiers consultés comme `FileChange(action="consulted")`.
* Les fichiers consultés apparaissent dans le graphe de co-occurrence (edges fichier↔commit).
* Aucun blob n'est stocké pour les fichiers consultés.
* Le prompt système du serveur MCP documente clairement le comportement attendu : ne mentionner QUE les documents véritablement utiles, contenant des informations inconnues avant consultation.
* Les fichiers consultés s'affichent distinctement dans `consult_commit` (ex: `[consulted]` vs `[modified]`).
* La sérialisation/désérialisation (`commit_to_dict`/`commit_from_dict`) supporte la nouvelle action.
