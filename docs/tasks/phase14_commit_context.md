# Phase 14 — Contexte de Commit (Prev/Next)

## 1. Contexte & Discussion (Narratif)
Lors d'une session de planification d'architecture, l'utilisateur a suggéré une amélioration UX pour l'outil MCP `consult_commit` : afficher, lors de la consultation d'un commit, les titres des commits parent (Précédent) et enfant (Suivant). 

L'objectif est d'offrir un aperçu chronologique ("qu'est-ce qui a suivi ? qu'est-ce qui précédait ?") sans obliger l'agent LLM à appeler répétitivement `get_recent_commits` ou de multiples recherches sémantiques. 
Cette approche a été retenue et validée par l'Architecte. Elle fluidifie l'exploration de la mémoire et renforce la continuité de contexte pour l'agent.

## 2. Fichiers Concernés
- `src/aivc/server.py` (Formatage du rendu de l'outil `consult_commit`)
- `src/aivc/core/workspace.py` ou `src/aivc/semantic/engine.py` (Ajout d'une logique pour identifier l'enfant direct)
- `src/tests/test_server.py` (Ajouts des tests d'affichage)

## 3. Objectifs (Definition of Done)
* Le message de retour de l'outil `consult_commit` inclut visuellement le titre et l'ID du commit Précédent (parent) et Suivant (enfant), s'ils existent.
* Ne pas alourdir la sortie (ajouter juste 2 lignes concises).
* L'absence de parent (premier commit) ou d'enfant (HEAD) doit être traitée sans erreur (affichée discrètement ou non affichée).
* Tests unitaires ajoutés ou mis à jour pour vérifier la présence de ces informations dans la réponse textuelle de l'outil.
