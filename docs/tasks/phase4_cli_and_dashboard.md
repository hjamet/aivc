# Phase 4 : CLI & Web Dashboard (Visualisation de la Mémoire)

## 1. Contexte & Discussion (Narratif)
> *Inspire-toi du style "Handover" : Raconte pourquoi on fait ça.*

Suite à la mise en place du serveur MCP (Phase 3), l'agent LLM dispose d'un accès total à sa mémoire à long terme (AIVC). Cependant, l'utilisateur a judicieusement fait remarquer que le développeur humain était "aveugle".
Il a été décidé de lancer une **Phase 4** double :
1. **Une CLI (`aivc`)** : Pour interagir rapidement en terminal (`status`, `log`, `search`, `commit`).
2. **Un Web Dashboard élégant** : Pour visualiser la structure de la mémoire sous forme de graphe interactif.

La demande spécifique de l'utilisateur pour le Dashboard :
- Visualisation sous forme de graphe où les **Noeuds = Fichiers (Documents)**.
- **Taille du noeud** : Proportionnelle au nombre de commits qui ont touché le fichier.
- **Couleur du noeud** : Basée sur l'arborescence des dossiers (les fichiers d'un même dossier/proches partagent des couleurs similaires).
- **Fonction de recherche ("Search")** : Effectue une recherche sémantique parmi les commits, puis **met en surbrillance** sur le graphe les noeuds (fichiers) liés à ces commits, et affiche les messages des commits correspondants.
Le tout doit être extrêmement propre, simple et visuellement époustouflant.

Liens :
- Fichier racine : [README.md](../../README.md)
- Moteur sémantique (pour la recherche) : `src/aivc/semantic/engine.py`
- Données du graphe : `src/aivc/semantic/graph.py` (qui a d'ailleurs une fonction `to_vis_data()`)

## 2. Fichiers Concernés
- `src/aivc/cli.py` (à créer)
- `src/aivc/web/` ou interface équivalente (HTML/JS/CSS statique ou mini-serveur Flask/FastAPI)
- `.agent/workflows/` (si des scripts spécifiques au run web sont nécessaires)

## 3. Objectifs (Definition of Done)
- **CLI** : Une ligne de commande `aivc` est accessible localement avec au minimum `aivc status`, `aivc log` et `aivc search "query"`.
- **Web App (Visualisation)** : Une interface web moderne et "premium" est accessible.
- **Topologie du Graphe** : Le graphe s'affiche avec des noeuds représentant les fichiers.
- **Esthétique (Encodage visuel)** : La taille des noeuds reflète leur fréquence de commit, et leur couleur reflète leur hiérarchie (dossier parent).
- **Interactivité (Recherche Sémantique)** : Une barre de recherche permet d'interroger la mémoire sémantique. Les résultats illuminent/filtrent les noeuds concernés dans le graphe et exposent les détails (notes) des commits pertinents.
- Le fallback en cas d'erreur de la CLI doit rester du crash pur ("Jamais de fallback", règle globale AIVC).
