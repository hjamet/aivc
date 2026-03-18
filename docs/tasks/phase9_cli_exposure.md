# Phase 9 — Exposition globale de la CLI

## 1. Contexte & Discussion (Narratif)
> L'utilisateur ne parvenait pas à exécuter la commande `aivc web` après l'installation (`command not found`).
- L'analyse asynchrone via le rôle Architect a révélé que les scripts `install.sh` et `install_dev.sh` installaient correctement le paquet dans un environnement virtuel isolé via `uv`, mais que le dossier `bin` du venv n'était pas exposé globalement dans le `$PATH` de l'utilisateur.
- La décision architecturale approuvée a été de rajouter une étape de création de lien symbolique (`symlink`) vers le chemin `~/.local/bin/aivc` en fin d'installation, pour que la CLI redescende sans effort d'incorporation.

## 2. Fichiers Concernés
- `install.sh`
- `install_dev.sh`
- `README.md`

## 3. Objectifs (Definition of Done)
- À la fin des scripts d'installation, un lien symbolique `~/.local/bin/aivc` doit repointer vers l'exécutable `aivc` natif localisé dans le venv respectif (prod ou dev).
- Rétro-compatibilité assurée (mkdir -p de `~/.local/bin` si non existant).
- Le `README.md` est mis à jour (Section Roadmap & Index).
