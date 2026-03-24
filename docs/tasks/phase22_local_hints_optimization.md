# Phase 22 — Optimisation des Hints Locaux (O(1) Index)

## 1. Contexte & Discussion (Narratif)
> L'Architecte a relevé un problème de performance sur la fonctionnalité introduite en Phase 21 : les hints de fichiers locaux. La méthode `find_local_equivalent` exécutait un `self.get_status()` complet, qui en plus d'itérer sur chaque fichier, chargeait la taille sur disque et interrogeait potentiellement la base SQLite pour compter le poids historique. Avec des milliers de fichiers en projet réel, cela causait des blocages de latence lors d'un `search_memory` distant.
> Après validation par l'utilisateur, et un filtrage strict des autres remarques non-prioritaires, l'objectif est d'implémenter un dictionnaire en mémoire agissant comme un "Index inversé", offrant un accès $O(1)$ par nom de fichier (basename).

## 2. Fichiers Concernés
- `src/aivc/core/workspace.py` (Ajout d'un point d'accès rapide aux chemins trackés)
- `src/aivc/semantic/engine.py` (Ajout du cache inversé, invalidation, et optimisation de `find_local_equivalent`)

## 3. Objectifs (Definition of Done)
* Un appel à `find_local_equivalent` ne déclenche plus l'instanciation de `FileStatus` pour tous les fichiers.
* Un index en mémoire fait correspondre chaque `basename` à une liste de `local_paths`.
* Cet index est construit paresseusement (au premier appel d'un hint) et mis en cache.
* Le cache est systématiquement invalidé si l'état du tracking change (`track`, `untrack`, ou nouveauté cachée lors d'un `create_commit`).
* La suite de tests unitaires existante continue de passer de façon robuste.
