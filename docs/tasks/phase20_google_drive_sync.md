# Cloud Sync + Async Commit (Phase 20)

## 1. Contexte & Discussion (Narratif)
Le besoin est de partager les mémoires (commits) entre différentes machines (ex: un PC fixe Windows, un WSL, un laptop) tout en gardant une source de vérité locale forte. La machine actuelle privilégie toujours son propre index local pour la rapidité, mais peut interroger les commits réalisés ailleurs. 

La synchronisation utilise **rclone** comme backend (supporte Google Drive, Dropbox, S3, OneDrive, etc.). L'utilisateur configure son remote via `rclone config`. AIVC ne gère pas l'authentification cloud elle-même.

En bonus, l'encodage sémantique de `create_commit` est rendu **asynchrone** pour accélérer la réponse du MCP.

## 2. Fichiers Concernés
- `src/aivc/config.py` — ajout `get_machine_id()`, `get_aivc_config()`
- `src/aivc/core/commit.py` — ajout champ `machine_id`
- `src/aivc/semantic/engine.py` — commit asynchrone (thread worker pour indexation)
- `src/aivc/semantic/indexer.py` — metadata `machine_id` dans ChromaDB
- `src/aivc/server.py` — `only_local` param, pull au démarrage, warnings distants
- `src/aivc/cli.py` — `aivc sync setup/status`, `aivc config`
- `src/aivc/sync/` (Nouveau module) — `sync.py` (rclone), `background.py` (thread daemon)
- `install.sh` — génération `~/.aivc/config.json`

## 3. Objectifs (Definition of Done)
- Chaque commit possède un `machine_id` clair (configurable dans `~/.aivc/config.json`, fallback hostname).
- L'encodage sémantique de `create_commit` est **asynchrone** — l'outil retourne immédiatement la liste des fichiers commités.
- La synchronisation vers le cloud se fait en arrière-plan via rclone (thread daemon).
- Le pull des commits distants n'a lieu qu'au **démarrage du serveur MCP** (thread de fond).
- Les blobs sont stockés individuellement sur le remote, téléchargés **à la demande** via `read_historical_file`.
- Les outils MCP (`search_memory`, `search_files_bm25`, `get_recent_commits`) supportent un paramètre `only_local` (False par défaut).
- Les résultats mentionnent `[Remote: <machine_id>]` pour les commits distants.
- `read_historical_file` / `consult_file` sur un fichier distant affichent un **warning** (pas d'erreur si Drive activé). Erreur claire si sync désactivée.
