# Phase 2 : Moteur Sémantique et Graphe de Connaissances

## 1. Contexte & Discussion (Narratif)

> La Phase 2 introduit l'intelligence de recherche. La recherche sémantique ne s'applique 
> **qu'aux notes Markdown des commits**.
>
> Suite aux retours de l'utilisateur, l'architecture d'indexation monte en gamme tout en 
> restant locale :
> 1. **Bi-Encoder** (`all-MiniLM-L6-v2`) : Pour dégrossir et récupérer rapidement un Top K.
> 2. **Cross-Encoder** : Pour reranker précisément le Top K et isoler le Top N ultra-pertinent.
>
> Tout cela tourne obligatoirement dans un environnement virtuel isolé (`~/.aivc/`) pour ne pas polluer l'OS cible.
> 
> Un ajout demandé est la **Visualisation**. Le graphe (Fichiers ↔ Commits) résultant de 
> la co-occurrence devrait pouvoir être visualisé via une interface web locale facultative.

## 2. Fichiers Concernés

- `src/aivc/semantic/indexer.py` — Base vectorielle (ChromaDB)
- `src/aivc/semantic/searcher.py` — Pipeline de reranking (Bi-encoder -> Cross-encoder)
- `src/aivc/semantic/graph.py` — Algorithme du graphe de co-occurrence
- `src/aivc/ui/server.py` — Mini-serveur web facultatif de visualisation (ex: FastAPI + Pyvis/D3)
- `install.sh` / `setup.py` — Création de l'isolation `~/.aivc`

## 3. Objectifs (Definition of Done)

* Indexation vectorielle locale avec `all-MiniLM-L6-v2`.
* Pipeline de Retrieval & Reranking avec Cross-Encoder pour une précision maximale.
* Graphe de co-occurrence mis à jour dynamiquement.
* Un serveur (commande `aivc --ui` ou équivalent) exposant une page web locale (HTML/JS) modélisant le graphe de manière interactive.
* L'environnement de fonctionnement doit être strictement limité à `~/.aivc/`.
* **Aucun fallback** : toute erreur doit crasher proprement.
