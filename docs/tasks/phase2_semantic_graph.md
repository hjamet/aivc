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
> **Décision Architecte (2026-03-18)** : L'interface visuelle (UI Web) est annulée pour le moment. L'installation sera gérée par un script `install.sh` bash automatisé (via `curl | bash`) qui injectera dynamiquement la configuration d'AIVC dans le fichier `mcp_config.json` de Gemini Antigravity, rendant l'intégration instantanée.
> L'intégration au `core` de la Phase 1 se fera via un wrapper `SemanticEngine` (Option B) pour conserver la pureté stdlib de la Phase 1.

## 2. Fichiers Concernés

- `pyproject.toml`
- `src/aivc/semantic/indexer.py` — Base vectorielle (ChromaDB)
- `src/aivc/semantic/searcher.py` — Pipeline de reranking (Bi-encoder -> Cross-encoder)
- `src/aivc/semantic/graph.py` — Algorithme du graphe de co-occurrence
- `src/aivc/semantic/engine.py` — Orchestrateur (wrapper autour de Workspace + Indexer + Graph)
- `install.sh` — Script Bash + setup du `mcp_config.json`

## 3. Objectifs (Definition of Done)

* Indexation vectorielle locale avec `all-MiniLM-L6-v2` via ChromaDB.
* Pipeline de Retrieval & Reranking avec Cross-Encoder pour une précision maximale.
* Graphe de co-occurrence mis à jour dynamiquement.
* Le moteur "SemanticEngine" wrappe le "Workspace" sans introduire de régression sur ce dernier.
* Un script `install.sh` fonctionnel, exécutable via pipe (`cat install.sh | bash`), qui configure le venv `uv` ET modifie le fichier `~/.gemini/antigravity/mcp_config.json` en parsant du json en python.
* L'environnement de fonctionnement doit être strictement limité à `~/.aivc/`.
* **Aucun fallback** : toute erreur doit crasher proprement.
