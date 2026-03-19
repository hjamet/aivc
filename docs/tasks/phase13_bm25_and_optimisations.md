# Phase 13 — Recherche Lexicale BM25 & Optimisation CoreIndex

## 1. Contexte & Discussion (Narratif)

> *Inspire-toi du style "Handover" : Raconte pourquoi on fait ça.*
Lors d'une session d'architecture, nous avons identifié que l'AIVC manquait d'un moyen de rechercher par mot-clé (lexical) dans le contenu des fichiers traqués (Phase 13 initiale). 

En parallèle, l'Architecte a repéré une dette technique majeure introduite lors de la Phase 15 (CoreIndex) : le constructeur `Workspace.__init__` parcourt systématiquement tout le dossier `commits/*.json` au démarrage pour vérifier si des commits historiques manquent dans l'index SQLite. Sur 50 000 commits, cette vérification ferait s'effondrer les temps de réponse de chaque appel CLI (`aivc status`, etc.). 

L'utilisateur a donc exigé de regrouper l'ajout de BM25 et cette optimisation critique en une seule grosse phase pour éviter de multiplier les mini-tâches, tout en demandant de déplacer la configuration ML codée en dur (ex: `all-MiniLM-L6-v2`) vers le nouveau fichier `config.py` fraîchement créé.

## 2. Fichiers Concernés

- `install.sh` et `install_dev.sh` (Ajout du hook de migration)
- `src/aivc/cli.py` (Nouvelle sous-commande `migrate`)
- `src/aivc/core/workspace.py` (Suppression de la migration synchrone)
- `src/aivc/config.py` (Ajout des constantes modèles ML)
- `src/aivc/semantic/indexer.py` (Utilisation de la config ML centralisée)
- `src/aivc/semantic/searcher.py` (BM25 & utilisation config ML)
- `src/aivc/semantic/engine.py` (Mise à disposition de la recherche BM25)
- `src/aivc/server.py` (Nouvel outil MCP pour BM25)
- `src/aivc/cli.py` (Nouvelle sous-commande CLI)

## 3. Objectifs (Definition of Done)

* **Migration Explicite (via Install)** : L'I/O lourde (le `glob` de JSON) est **totalement supprimée** de `Workspace.__init__`. La logique de migration est déplacée vers une nouvelle commande CLI `aivc migrate`.
* **Hooks d'Installation** : Les scripts `install.sh` et `install_dev.sh` exécutent automatiquement `aivc migrate` à la fin de leur exécution pour garantir une transition transparente pour l'utilisateur.
* **Centralisation ML** : Les identifiants des modèles (`all-MiniLM-L6-v2`, `ms-marco-MiniLM-L-6-v2`, etc.) ne sont plus codés en dur dans la logique sémantique mais extraits depuis `src/aivc/config.py`.
* **Recherche BM25** : Le système implémente une base BM25 (via `rank_bm25` ou un équivalent) sur le contenu en texte brut des fichiers traqués par AIVC, pour permettre de chercher du *code exact* (noms de fonctions, variables) là où le sémantique échoue.
* **Exposition MCP / CLI** : La recherche lexicale BM25 est exposée via un outil MCP `search_files_bm25` et une sous-commande CLI.
* Les tests de la suite s'exécutent avec succès et sans régression sur la performance du système.
