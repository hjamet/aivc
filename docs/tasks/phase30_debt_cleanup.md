# Phase 30 : Unification du Vocabulaire & Nettoyage de la Dette

## 1. Contexte & Discussion (Narratif)
> *Handover note: C'est l'heure de payer la dette technique accumulée suite au pivot de la Phase 29 !*

Lors de la Phase 29, AIVC a officiellement opéré sa transition d'un "outil de versionnage" (Git pour agents) vers un "Système de Mémoire" (Long-Term Memory). Nous avons renommé tous les outils MCP publics (`remember`, `recall`, etc.) pour correspondre à ce nouveau paradigme cognitif.

Cependant, le backend (les classes internes, le moteur d'indexation, la base SQLite) est resté figé sur le vocabulaire "Commit". Cette dissonance cognitive (Front = Memory, Back = Commit) rend le code difficile à appréhender pour les agents qui devront le maintenir. L'objectif est donc d'unifier ce vocabulaire de bout en bout en remplaçant la notion interne de "Commit" par "Memory" partout où c'est sémantiquement valable.

En parallèle, la Phase 29 a désactivé la synchronisation des contenus de fichiers (blobs) vers le Cloud pour des raisons de sécurité et de performances. Or, le code de gestion (`push_blob`, `fetch_blob`, caches locaux de blobs) git encore dans le module `drive.py`, alourdissant inutilement le système. Il faut purger ce code mort.

## 2. Fichiers Concernés
- `src/aivc/core/commit.py` (à renommer potentiellement en `memory.py` ou modifier les classes `Commit` -> `Memory`)
- `src/aivc/core/workspace.py`
- `src/aivc/core/blob_store.py`
- `src/aivc/semantic/indexer.py` et `searcher.py`
- `src/aivc/sync/drive.py` (Purge du code mort)
- Bases de données SQLite et schémas JSON (Attention à la rétro-compatibilité ou au script de migration).

## 3. Objectifs (Definition of Done)
*   **Backend Sémantique Unifié** : Les classes `Commit`, les fonctions `create_commit()`, les tables SQLite `commits` et les variables associées sont renommées en `Memory`, `create_memory()`, `memories`, etc., sur l'ensemble du dépôt.
*   **Purge de la Synchronisation** : Le module `drive.py` et `engine.py` ne contiennent plus aucune trace de la logique d'upload/download des `blobs`. Le code est focalisé à 100% sur la synchronisation des JSON de mémoires.
*   **Transparence Publique** : Ce refactoring doit être complètement invisible pour l'utilisateur final et l'API MCP (qui utilise déjà le vocabulaire "Memory"). Les tests doivent continuer à passer.
