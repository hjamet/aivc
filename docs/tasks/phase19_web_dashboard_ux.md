# Phase 19 — Web Dashboard UX : Sidebar Git Log, File History, Fix Forces

## 1. Contexte & Discussion (Narratif)

Le Web Dashboard AIVC (`aivc web`) a été implémenté en Phase 4 avec Cytoscape.js.
Actuellement, la sidebar est cachée et ne s'ouvre que lors d'une recherche sémantique.
Le système de forces (layout cose) se relance automatiquement après chaque drag de nœud,
ce qui provoque un comportement buggy où tous les nœuds se repositionnent involontairement.

L'utilisateur souhaite trois améliorations :
1. **Sidebar ouverte au démarrage** avec un git log des 10 derniers commits (infinite scroll)
2. **Historique fichier au clic sur un nœud** — la sidebar affiche les commits ayant touché ce fichier
3. **Suppression du relayout automatique** — le drag doit déplacer uniquement le nœud ciblé

## 2. Fichiers Concernés

- `src/aivc/web/dashboard.py` — Nouveaux endpoints `/api/log` et `/api/file-history/`
- `src/aivc/web/static/index.html` — Refonte sidebar, suppression forces, clic nœud
- `src/aivc/semantic/engine.py` — Ajout `get_log` avec `offset`
- `src/aivc/core/workspace.py` — Support `offset` dans `get_log()`
- `src/aivc/semantic/graph.py` — Enrichissement `get_file_commits` avec métadonnées
- `src/tests/test_dashboard.py` — Tests des nouveaux endpoints

## 3. Objectifs (Definition of Done)

* **Au démarrage**, la sidebar est ouverte et affiche les 10 derniers commits (titre, date, ID court).
* **En scrollant** dans la sidebar, les commits plus anciens se chargent automatiquement (infinite scroll).
* **Au clic sur un nœud** du graphe, la sidebar bascule en mode "historique fichier" montrant tous les commits ayant touché/consulté ce fichier, ordonnés chronologiquement.
* **Le drag d'un nœud** ne provoque plus de relayout global : seul le nœud déplacé bouge.
* Les tests existants passent toujours. Nouveaux tests pour les endpoints ajoutés.
