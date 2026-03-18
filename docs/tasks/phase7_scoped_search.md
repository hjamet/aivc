# Phase 7 — Scoped Semantic Search (Filtrage par Glob)

## 1. Contexte & Discussion (Narratif)

Lors de l'utilisation réelle d'AIVC comme mémoire long-terme, l'agent (ou l'utilisateur CLI) veut souvent restreindre sa recherche sémantique à un sous-ensemble de fichiers. Exemple : "Qu'est-ce que j'ai fait sur l'authentification dans `src/api/auth/` ?" ou "Quels commits ont touché `*.py` dans `tests/` ?".

Actuellement, `search_memory` cherche dans **tous** les commits sans distinction. Sur un gros historique, cela noie les résultats pertinents dans du bruit.

L'idée est d'ajouter un paramètre optionnel `filter_glob` (vide par défaut = pas de filtrage) qui restreint la recherche aux commits ayant modifié au moins un fichier correspondant au pattern glob fourni.

### Décisions techniques
- **Approche retenue** : Pre-filtrage via le graphe SQLite (`CooccurrenceGraph`), puis passage des `commit_id` valides comme clause `$in` dans ChromaDB avant le Bi-Encoder. Cela réduit l'espace de recherche au maximum.
- **Fallback** : Si la liste de commit IDs est trop grande pour ChromaDB `$in`, filtrer en Python post-Bi-Encoder (avant Cross-Encoder).
- **API** : Le paramètre est optionnel et vide par défaut (comportement actuel inchangé).

## 2. Fichiers Concernés

- `src/aivc/semantic/graph.py` — Nouvelle méthode `get_commits_by_glob(pattern)`
- `src/aivc/semantic/indexer.py` — Ajout support `filter_ids` dans `query()`
- `src/aivc/semantic/searcher.py` — Propagation du filtre dans le pipeline
- `src/aivc/semantic/engine.py` — Propagation du paramètre dans la façade
- `src/aivc/server.py` — Ajout paramètre `filter_glob` à l'outil MCP `search_memory`
- `src/aivc/cli.py` — Ajout option `--glob` / `-g` à la commande `aivc search`
- `src/tests/test_graph.py` — Tests pour `get_commits_by_glob`
- `src/tests/test_searcher.py` — Tests pour le pipeline filtré

## 3. Objectifs (Definition of Done)

* `search_memory(query, filter_glob="src/aivc/semantic/*.py")` ne retourne que les commits ayant touché des fichiers dans `src/aivc/semantic/` avec extension `.py`.
* `aivc search "mon query" --glob "src/aivc/core/*"` fonctionne en CLI.
* Si `filter_glob` est vide (défaut), le comportement est **strictement identique** à l'actuel.
* Le filtrage fonctionne avec les chemins absolus stockés dans le graphe.
* Les tests existants continuent de passer sans modification.
