# Google Drive Sync (Phase 20)

## 1. Contexte & Discussion (Narratif)
Le besoin est de partager les mémoires (commits) entre différentes machines (ex: un PC fixe Windows, un WSL, un laptop) tout en gardant une source de vérité locale forte. La machine actuelle privilégie toujours son propre index local pour la rapidité, mais peut interroger les commits réalisés ailleurs. 

Cela évite de perdre le contexte lorsqu'on change de poste. L'enjeu technique majeur est de ne pas bloquer le serveur MCP pendant les I/O réseau avec Google Drive. L'agent doit également être clairement alerté lorsqu'il consulte des informations ne résidant pas sur sa machine active.

## 2. Fichiers Concernés
- `src/aivc/config.py`
- `src/aivc/cli.py`
- `src/aivc/server.py`
- `src/aivc/core/commit.py`
- `src/aivc/core/workspace.py`
- `src/aivc/sync/` (Nouveau dossier)

## 3. Objectifs (Definition of Done)
- Un utilisateur peut s'authentifier à Google Drive via une nouvelle commande CLI `aivc auth drive`.
- Chaque commit possède un identifiant de machine clair (configurable) pour distinguer son origine.
- Lors de la création d'un commit ou d'un tracking, la synchronisation vers Drive s'effectue en arrière-plan afin de ne pas bloquer les temps de réponse du MCP.
- La structure sur le Cloud sépare proprement les dossiers de chaque machine.
- Les outils de recherche MCP (`search_memory`, `search_files_bm25`, `get_recent_commits`) supportent un nouveau paramètre `only_local` (False par défaut).
- Les résultats de recherche mentionnent explicitement si un commit ou un fichier provient d'une *autre* machine.
- Un message d'erreur clair empêche la lecture d'un fichier complet via `consult_file` ou `read_historical_file` depuis une autre machine si l'historique Drive n'est pas activé/téléchargé.
