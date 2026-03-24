# Phase 21 : Async & Sync Consolidation

## 1. Contexte & Discussion (Narratif)
> *Inspire-toi du style "Handover" : Raconte pourquoi on fait ça.*
Suite au déploiement de la Phase 20 (Cloud Sync), l'Architecte a levé une alerte de dette technique sur trois aspects cruciaux :
1. **Verrouillage Réseau/CPU** : L'indexation sémantique (qui demande du CPU) et l'upload cloud (qui demande du réseau) partagent la même file d'attente et le même thread worker dans `SemanticEngine`. Si la connexion est lente (gros blob à uploader), ChromaDB ne peut plus indexer les nouveaux commits.
2. **Extinction Violente** : Le worker est un démon (`daemon=True`). Si l'agent redémarre l'environnement ou éteint le serveur, le processus se coupe immédiatement, risquant de corrompre l'index ChromaDB (SQLite local) ou d'interrompre un upload.
3. **Partitionnement des Blobs** : Sur le cloud, les blobs étaient triés par `machine_id`. L'utilisateur a très justement fait remarquer que si deux machines travaillent sur le même dépôt Git, on aurait des historiques séparés et du contenu dupliqué. En utilisant un dossier cloud unique et partagé pour les blobs, le fonctionnement *Content-Addressable* d'AIVC (SHA-256) garantira que le même fichier n'est pas uploadé en double, car son hash est identique. La résolution au niveau du graphe (chemins absolus différents) pourra être traitée plus tard.

## 2. Fichiers Concernés
- `src/aivc/semantic/engine.py`
- `src/aivc/sync/sync.py`
- `src/aivc/sync/background.py`
- `src/aivc/server.py`

## 3. Objectifs (Definition of Done)
* **Découplage des Workers** : Séparer l'indexation ChromaDB et le Push Cloud dans deux threads et files d'attente distinctes (ou utiliser intelligemment un pool) pour que l'I/O réseau ne bloque jamais le CPU.
* **Graceful Shutdown** : Implémenter et appeler une méthode d'arrêt propre sur l'engine pour s'assurer que les queues se vident (avec un timeout raisonnable) avant l'extinction du script.
* **Pool Global de Blobs Cloud** : Modifier la structure distante générée par Rclone pour que le dossier `blobs/` soit mutualisé entre toutes les machines (`AIVC_Sync/blobs/`), évitant ainsi la duplication de stockage pour des fichiers identiques versionnés sur des machines différentes.
* **Hint de Fichier Local Probable** : Lors de l'affichage de commits distants (dans `search_memory`, `get_recent_commits`, `consult_commit`), identifier les fichiers distants qui ont probablement un équivalent local (même basename + racine commune à profondeur 1 + historique de blobs partagé) et afficher un hint entre parenthèses : `(probablement <chemin_local> localement)`. Cela aide l'agent à comprendre que le fichier distant `/home/user2/repo/src/main.py` correspond à son `/home/user1/repo/src/main.py` local.
