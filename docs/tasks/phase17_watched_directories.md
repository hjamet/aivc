# Phase 17 — Dossiers Surveillés (JIT Watcher)

## 1. Contexte & Discussion (Narratif)

> *Suite aux discussions architecturales après la Phase 16.*

L'utilisateur exige un système de **surveillance intégrale, automatique et continue** des gros dossiers, déchargeant complètement l'agent LLM de la gestion manuelle du tracking. L'objectif est d'avoir un "Always-On Surveilled Scope" piloté par le serveur MCP.

L'Architecte a acté que le modèle le plus robuste est une architecture hybride **Daemon MCP Watcher + Startup Sync**. 
1. **La réalité du Watcher** : Un watcher (ex: `watchdog`) ne capte les événements de création de fichier **que lorsqu'il tourne**. Si le serveur MCP est éteint pendant que l'utilisateur travaille, ces créations seront manquées.
2. **La solution** : Pour garantir un système infaillible, le serveur MCP doit **absolument** faire un *Startup Scan* (via `os.walk`) à chaque démarrage pour rattraper son retard, PUIS lancer le *Watcher temps-réel* pour un confort total en continu.

### 🚨 Règle Critique : Fichiers Supprimés
Gérer les "nouveaux fichiers" est simple (on les `track()`). Mais la gestion des **fichiers supprimés** comporte un piège mortel :
Si le Watcher détecte qu'un fichier a été supprimé du disque dur, **IL NE DOIT JAMAIS** appeler `untrack()`. Mettre un fichier en "untrack" l'efface de la mémoire d'AIVC, ce qui empêcherait le prochain `create_commit` de détecter l'action de suppression (et de l'inscrire dans l'historique de la base). 
Le Watcher ne doit réagir qu'aux ajouts. Le moteur de diff (`compute_diff`) d'AIVC s'occupera naturellement d'enregistrer les suppressions lors du prochain commit.

## 2. Fichiers Concernés

- `pyproject.toml` (Ajout de la dépendance `watchdog`)
- `src/aivc/core/workspace.py` (Mise à jour de `track`/`untrack` pour gérer le `watched_dirs`)
- `src/aivc/cli.py` (Pas de nouvelles commandes, `track` et `untrack` gèrent dynamiquement la surveillance)
- `src/aivc/server.py` (Implémentation du thread Watcher et du scan de démarrage, suppression des outils `watch_directory`)

## 3. Objectifs (Definition of Done)

* **Surveillance automatique** : Si `aivc track <dir>` est appelé avec un dossier, il est automatiquement rajouté aux `watched_dirs`.
* **Arrêt de surveillance** : Si `aivc untrack <dir>` est appelé avec un dossier, il supprime la surveillance ET détruit l'historique de tous les fichiers à l'intérieur.
* **Scan au Démarrage (Sync)** : La fonction `serve()` effectue le scan JIT habituel.
* **Watcher Réactif** : Un thread `watchdog` appelle `track(path)` sur les nouveaux fichiers créés dans ces dossiers.
* **Protection de l'Historique** : Le Watcher ignore volontairement les `FileDeletedEvent`.
