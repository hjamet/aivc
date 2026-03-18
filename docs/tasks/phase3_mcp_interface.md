# Phase 3 : Interface MCP et Outils Exposés

## 1. Contexte & Discussion (Narratif)

> La Phase 3 gère le goulot d'étranglement de l'attention du LLM : **le Contexte**.
>
> Le flux de recall a été redésigné en entonnoir :
> L'agent ne reçoit **jamais** les messages complets ou le contenu des fichiers lors d'une recherche, 
> pour éviter de noyer ses tokens. `search_memory` renvoie juste des titres et des listes d'IDs. 
> L'agent doit explicitement appeler `consult_commit` s'il veut creuser l'historique.
>
> Côté gestion de l'espace, la fonction `prune_history` a été fusionnée dans `untrack`.
> L'appel à `untrack` est désormais l'outil massif de libération d'espace (destructif).

## 2. Fichiers Concernés

- `src/aivc/server.py` — Point d'entrée du serveur MCP
- `src/aivc/tools/commit_tool.py` — Outil `create_commit`
- `src/aivc/tools/search_tool.py` — Outils `search_memory` et `consult_commit`
- `src/aivc/tools/workspace_tool.py` — Outils `get_status` et `untrack`
- `src/aivc/tools/history_tool.py` — Outils de lecture historique

## 3. Objectifs (Definition of Done)

* Le serveur MCP doit exposer les outils suivants :
  - **`create_commit(title, detailed_markdown)`** : Consigne explicite pour que l'agent génère un compte-rendu massif de son raisonnement. Les fichiers modifiés sont auto-associés.
  - **`search_memory(query)`** : Retourne la liste des commits (Titre, Date, ID) et les fichiers associés potentiels. **Interdiction stricte d'inclure le contenu textuel lourd des commits ou des fichiers dans cette réponse**.
  - **`consult_commit(commit_id)`** : Retourne la note Markdown complète du commit, et les diffs (ou liens de diffs) générés lors de ce commit.
  - **`get_status()`** : Expose au LLM le bilan de charge (Taille actuelle des fichiers ET poids de leur historique respectif).
  - **`untrack(file_path)`** : Retrait du tracking ET suppression de l'historique (déclenche le Garbage Collector). Action destructive documentée dans le prompt.
  - **`consult_file(file_path)`**, **`read_historical_file(file_path, commit_id)`**, **`get_diff(file_path, a, b)`** : Consultations standards.
* Une **consigne système (prompt)** doit instruire l'agent des flux d'utilisation (Entonnoir de recall, usage de la mémoire).
* **Aucun fallback** : toute erreur doit crasher proprement.
