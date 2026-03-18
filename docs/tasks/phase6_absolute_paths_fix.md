# Phase 6 : Consolidation des Chemins Absolus & CLI

## 1. Contexte & Discussion (Narratif)
Lors du crash test du MVP par l'Architecte, deux problèmes ont été levés : 
- L'apparition de chemins WSL `/mnt/c/...` bloquants.
- Les anciens commits (Phases 1-4) stockaient des chemins relatifs, ce qui brise la fonctionnalité `read_historical_file` depuis le passage aux chemins absolus (Phase 5).

Après discussion, l'utilisateur a confirmé vouloir conserver l'architecture basée sur les **chemins absolus**. L'objectif est donc d'assainir la base de données AIVC pour que l'historique complet soit 100% absolu, et d'ajouter une fonctionnalité manquante (`track`) à la CLI.

## 2. Fichiers Concernés
- `.aivc/storage/commits/*.json` (Migration)
- `src/aivc/cli.py` (Ajout de commande)

## 3. Objectifs (Definition of Done)
* Rédiger et exécuter un script de migration qui convertit rétroactivement tous les chemins relatifs des vieux commits en chemins absolus (en se basant sur la racine du projet actuel).
* Nettoyer les traces de `/mnt/c/` restantes si nécessaire.
* Vérifier que `consult_file` et `read_historical_file` parviennent à relire un fichier du tout premier commit.
* Implémenter la commande `aivc track <path>` pour que l'utilisateur n'ait pas à passer par du code Python pour indexer un nouveau fichier.
