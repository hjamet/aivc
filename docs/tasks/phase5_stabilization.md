# Phase 5 : Stabilisation et Résolution de Bugs (MVP)

## 1. Contexte & Discussion (Narratif)
> Suite aux tests exhaustifs du serveur MCP et du Dashboard Web, nous avons identifié plusieurs bugs critiques qui empêchaient une utilisation fluide, notamment dans des contextes d'agents comme Cursor ou Claude Desktop. L'un des problèmes majeurs était que l'agent perdait la trace des fichiers (affichés comme "missing" par `get_status`) à cause d'un conflit de répertoire courant (CWD). De plus, l'interface web chargeait indéfiniment lorsque les CDN de Cytoscape n'étaient pas joignables. L'objectif de cette phase est de corriger ces défauts de conception pour rendre AIVC robuste, autonome (zéro dépendance CDN externe) et résilient aux environnements de lancement aléatoires.

## 2. Fichiers Concernés
- `src/aivc/core/workspace.py`
- `src/aivc/cli.py`
- `src/aivc/web/dashboard.py`
- `src/aivc/web/static/index.html`
- `src/aivc/web/static/vendor/` (nouveau dossier)

## 3. Objectifs (Definition of Done)
- Un fichier nouvellement traqué l'est via son chemin absolu (résolu lors de l'appel à `track()`). La vue status fonctionne indépendamment du répertoire depuis lequel l'agent ou le CLI est lancé.
- Le Dashboard Web inclut les fichiers `cytoscape.min.js` et `cytoscape-fcose.js` localement dans le dossier `static/vendor`. Il n'y a plus aucun appel réseau externe dans le JS.
- En cas de conflit réseau (le port 8765 étant souvent utilisé, par ex. par `semcp`), le serveur web itère automatiquement sur les ports suivants (+1) jusqu'à trouver un port disponible.
- Les appels HTTP `HEAD` sur les endpoints `/api/*` ne retournent plus de `404` mais un statut `200` sans `body`.
- L'ensemble des tests unitaires passe toujours sans erreur (et les tests existants sur `workspace.py` gèrent correctement la mutation de nom de chemin si nécessaire).
