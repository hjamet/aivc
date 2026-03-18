# Phase 1 : Moteur de Versioning Interne (Core)

## 1. Contexte & Discussion (Narratif)

> Le moteur de versioning interne est la **fondation absolue** du projet AIVC.
>
> Le stockage est adressable par contenu (SHA-256), à l'image de Git.
> Les blobs sont immuables, ce qui donne une déduplication native.
> Un fichier X modifié 10 fois créera au maximum 10 blobs s'il change à chaque fois.
>
> **La consigne de l'Architecte (Garbage Collection)** :
> L'utilisateur a demandé que l'action `untrack` supprime également tout l'historique d'un fichier
> pour libérer de l'espace.
> Attention danger : Puisque les blobs sont dédupliqués, un fichier `A` et un fichier `B`
> peuvent partager un même blob. Si on `untrack` A et qu'on supprime bêtement ses blobs, 
> on corrompt l'historique de B !
> Il FAUT implémenter un système de **Reference Counting (GC)**. Les blobs ne sont physiquement 
> supprimés du disque que lorsque plus aucun fichier/commit ne les référence.

## 2. Fichiers Concernés

- `src/aivc/core/blob_store.py` — Stockage (SHA-256 blobs) avec Refcounter / GC
- `src/aivc/core/commit.py` — Données commit (Titre court + Markdown détaillé)
- `src/aivc/core/diff.py` — Détection des fichiers modifiés
- `src/aivc/core/workspace.py` — Gestion de l'espace de tracking et des tailles d'historique
- `src/tests/*`

## 3. Objectifs (Definition of Done)

* Le système peut stocker des blobs immuables (SHA-256).
* Le système crée des commits avec **Titre** et **Note Markdown détaillée**.
* Implémentation de la logique de **Garbage Collection (Refcount)** : la suppression de l'historique d'un fichier lors d'un `untrack` ne doit corrompre aucun autre fichier.
* La méthode `get_status` du workspace doit calculer et exposer :
  - La liste des fichiers surveillés
  - La taille de chaque fichier sur le disque actuel
  - **La taille de l'historique (blobs exclusifs + partagés)** consommé par ce fichier.
* **Aucun fallback** : toute erreur doit crasher proprement avec un message explicite.
