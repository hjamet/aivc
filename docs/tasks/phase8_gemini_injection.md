# Phase 8 — Injection GEMINI.md (Agent Best Practices)

## 1. Contexte & Discussion (Narratif)

Après la Phase 7, AIVC est un MVP fonctionnel avec recherche sémantique filtrée. Cependant, un problème critique subsiste : **l'agent LLM qui utilise AIVC ne sait pas comment bien l'utiliser**.

Le script `install.sh` configure le serveur MCP mais ne transmet aucune instruction d'usage à l'agent. Or, la qualité de la mémoire AIVC dépend directement des pratiques de l'agent :
- Commiter trop rarement = trous de mémoire
- Messages de commit trop courts = recall dégradé
- Ne pas explorer sa mémoire au démarrage = redondances, erreurs répétées

L'idée est que `install.sh` injecte automatiquement un bloc de bonnes pratiques dans `~/.gemini/GEMINI.md` (fichier de règles globales de l'agent Gemini/Antigravity).

### Décisions techniques
- **Idempotence** : Marqueurs HTML `<!-- AIVC:START -->` / `<!-- AIVC:END -->` pour encadrer le bloc. Si déjà présent, le contenu entre les marqueurs est remplacé.
- **Non-destructif** : Le reste du fichier GEMINI.md n'est jamais modifié.
- **Contenu** : Règles prescriptives pour l'agent LLM (commiter souvent, explorer la mémoire, messages détaillés).

## 2. Fichiers Concernés

- `install.sh` — Ajout d'une étape 6 : injection du bloc AIVC dans `~/.gemini/GEMINI.md`

## 3. Objectifs (Definition of Done)

* Après `bash install.sh`, le fichier `~/.gemini/GEMINI.md` contient un bloc AIVC entre marqueurs.
* Si `install.sh` est relancé, le bloc est **mis à jour** (pas dupliqué).
* Le bloc contient les recommandations suivantes :
  - Commiter (via l'outil `create_commit`, pas via git) à la moindre modification
  - Toujours commencer par `get_recent_commits` + **5 `search_memory` minimum** pour reconstruire le contexte de travail
  - Consulter l'historique des fichiers (`consult_file`) et l'historique des commits (`consult_commit`) pour comprendre les liens et l'histoire
  - Ne pas tenter de modifications déjà faites dans le passé
  - Messages de commit très détaillés : erreurs rencontrées, résolutions, décisions prises, observations, recommandations futures
* Le contenu existant de `~/.gemini/GEMINI.md` est préservé intégralement.
