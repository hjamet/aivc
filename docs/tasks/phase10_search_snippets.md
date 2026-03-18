# Phase 10 — Search Result Snippets

## 1. Contexte & Discussion (Narratif)
Lors de la session d'architecture du 18 mars 2026, on a constaté que les résultats de `search_memory` manquent de contexte : ils n'affichent qu'un titre court et un score brut. Le choix du bon commit est quasi impossible sans appeler `consult_commit` sur chaque résultat, ce qui sature le contexte de l'agent.

L'utilisateur a insisté sur deux points :
- **Pas de snippet de fichier** : certains fichiers sont binaires (PDF, images) et ça risque de saturer le contexte.
- **Snippet de la note du commit** : c'est la bonne granularité. La note est toujours du Markdown lisible et contient le "souvenir" sémantique.
- **Alternative complémentaire** : pousser les agents à écrire des titres plus longs (4-5 phrases) dans les instructions système, pour que même sans snippet, le titre soit suffisamment informatif.

L'idée d'un `aivc diff` a été explicitement rejetée par l'utilisateur (ralentirait l'agent, pas de valeur ajoutée car on veut toujours tout commiter).

## 2. Fichiers Concernés
- `src/aivc/semantic/searcher.py` — Le pipeline Bi-Encoder → Cross-Encoder retourne déjà un `SearchResult`. C'est ici qu'il faut ajouter le champ `snippet`.
- `src/aivc/server.py` — Le formattage MCP des résultats de `search_memory`.
- `src/aivc/cli.py` — La commande `aivc search` qui affiche les résultats en terminal.
- `src/tests/test_searcher.py` — Tests unitaires du searcher.

## 3. Objectifs (Definition of Done)
* Chaque résultat de `search_memory` (MCP et CLI) contient un extrait de ~200 caractères de la note du commit qui a matché.
* L'extrait est centré sur la portion la plus pertinente de la note (celle qui a le meilleur score de similarité avec la requête, si possible).
* Aucune régression sur les tests existants.
* Le Dashboard Web (`/api/search`) retourne aussi le snippet (il le fait déjà côté frontend, vérifier la cohérence).
