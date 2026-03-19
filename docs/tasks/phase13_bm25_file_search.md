# Phase 13 — Recherche BM25 sur Fichiers Traqués

## 1. Contexte & Discussion (Narratif)

Lors de la session d'architecture du 19 mars 2026, l'utilisateur a proposé d'ajouter une recherche **lexicale/keyword** (style BM25) sur le contenu des fichiers traqués. Actuellement, `search_memory` opère sur les notes de commit (sémantique). Il n'existe aucun moyen de chercher dans le contenu des fichiers eux-mêmes.

### Décisions techniques

- **Bibliothèque** : `bm25s` — pure Python, ultra-léger (~50KB), pas de modèle ML.
- **Scope** : Uniquement la **version courante** des fichiers traqués (pas l'historique).
- **Indexation incrémentale** : À chaque `create_commit`, seuls les fichiers du commit sont ré-indexés (pas un full rebuild).
- **Fichiers binaires** : Exclus du contenu indexé, **mais leur titre (nom de fichier) est indexé**.
- **Glob optionnel** : L'outil accepte un filtre glob facultatif pour restreindre la recherche à des dossiers/extensions spécifiques (ex: `*.py`, `docs/**/*.md`).

### Nom de l'outil

`search_files(query, glob?)` — clairement distingué de `search_memory` (notes de commit).

## 2. Fichiers Concernés

- `src/aivc/search/bm25_index.py` (NOUVEAU) — Moteur BM25 (index, tokenization, recherche)
- `src/aivc/semantic/engine.py` — Intégration de l'indexeur BM25
- `src/aivc/server.py` — Nouvel outil MCP `search_files`
- `src/aivc/server.py` — Mise à jour du `_SYSTEM_PROMPT`
- `src/aivc/cli.py` — Éventuellement une commande CLI `aivc search-files`
- `src/tests/test_bm25_index.py` (NOUVEAU) — Tests unitaires
- `pyproject.toml` — Ajout de la dépendance `bm25s`

## 3. Objectifs (Definition of Done)

* Un index BM25 est maintenu sur le contenu textuel (UTF-8) des fichiers traqués.
* L'index est mis à jour incrémentalement à chaque `create_commit` (seuls les fichiers du commit).
* Les fichiers non-UTF-8 sont exclus du contenu indexé mais leur nom de fichier reste recherchable.
* L'outil MCP `search_files(query, glob?)` retourne les fichiers les plus pertinents avec un score de relevance.
* Le filtre glob optionnel permet de restreindre la recherche (dossiers, extensions).
* La recherche est rapide (O(ms)) et le footprint mémoire est minimal.
* Le prompt système documente l'outil et sa distinction avec `search_memory`.
