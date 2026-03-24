# Phase 23 — Synchronisation d'État et Reload JIT (Multi-processus)

## 1. Contexte & Discussion (Narratif)
> L'Architecte a détecté une faille critique lors de la revue de la Phase 22 : le serveur MCP AIVC tourne en processus long (daemon) et charge `workspace.json` en mémoire une seule fois au démarrage. Si la CLI (`aivc track`, `aivc untrack`, ou toute autre exécution éphémère) modifie ce fichier sur le disque, le serveur MCP reste avec un état "fantôme" (stale state) totalement désynchronisé.
> Conséquence directe : si le serveur MCP crée un commit après que la CLI ait modifié le tracking, il écrase le fichier `workspace.json` avec son état périmé, corrompant potentiellement l'historique des commits (fork de chaîne). De plus, le cache O(1) des hints locaux (Phase 22) ne sera jamais invalidé par un changement CLI.
> L'utilisateur a validé l'ajout de cette tâche à la roadmap.

## 2. Fichiers Concernés
- `src/aivc/core/workspace.py` (Rechargement conditionnel de `workspace.json` via `mtime`)
- `src/aivc/semantic/engine.py` (Invalidation du cache hints suite au reload)

## 3. Objectifs (Definition of Done)
* `Workspace` détecte automatiquement si `workspace.json` a été modifié par un processus externe (comparaison du `mtime` / `os.path.getmtime()`).
* Avant chaque opération publique (`get_status`, `create_commit`, `track`, `untrack`, `get_tracked_paths`), `Workspace` recharge l'état si le fichier a changé.
* Le `SemanticEngine` invalide son cache d'index inversé (`_local_hints_index`) lorsque le `Workspace` signale un rechargement.
* La suite de tests unitaires existante continue de passer.
* Aucun scénario CLI + MCP ne peut corrompre l'historique des commits.
