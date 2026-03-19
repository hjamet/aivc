# Phase 16 — Fiabilisation BM25 & UX CLI

## 1. Contexte & Discussion (Narratif)

> *Suite aux retours post-déploiement de la Phase 13.*

Lors de la revue architecturale de la Phase 13, deux dettes techniques critiques ont été identifiées :
1. **Performance BM25** : L'implémentation de `search_files_bm25` lit et tokenise tous les fichiers traqués depuis le disque à chaque appel. Sur un grand dépôt, les I/O et la tokenisation répétée ralentissent considérablement la recherche.
2. **UX CLI** : Lorsqu'un humain utilise le CLI (ex: `aivc status`) sans que la variable `AIVC_STORAGE_ROOT` ne soit définie dans son prompt (contrairement à l'environnement MCP), l'application crash brutalement au lieu d'utiliser le répertoire par défaut.

Cette phase vise à pérenniser l'outil de recherche lexicale pour qu'il soit instantané sur des milliers de fichiers, et à rendre le CLI agréable d'utilisation "out of the box".

## 2. Fichiers Concernés

- `src/aivc/cli.py`
- `src/aivc/semantic/engine.py`
- `src/aivc/search/bm25_index.py` (NOUVEAU)
- `src/tests/test_cli.py`
- `src/tests/test_engine.py` (ou `test_bm25.py`)
- `README.md`
- `docs/index_architecture.md` (ou similaire, à mettre à jour)

## 3. Objectifs (Definition of Done)

* **UX CLI fluide** : Le CLI utilise le fallback par défaut (`~/.aivc/storage`) si la variable d'environnement `AIVC_STORAGE_ROOT` n'est pas définie. L'utilisateur n'a plus besoin d'éditer son `.bashrc`.
* **Cache de Tokenisation BM25** : Les opérations lourdes (lecture disque et tokenisation regex) sont mises en cache. Un index SQLite (ex: `bm25_cache.db`) stocke les tokens de chaque fichier avec son `mtime` ou sa taille.
* **Mise à jour incrémentale** : Lors d'une recherche BM25, seuls les fichiers dont le `mtime` ou la taille a changé depuis la dernière mise en cache sont relus et re-tokenisés.
* **Performance** : La recherche BM25 `search_files_bm25` répond en moins de 100ms sur un corpus en cache.
* **Compatibilité** : On conserve la librairie `rank_bm25` actuelle, le gain de performance provenant de l'élimination des I/O inutiles.
