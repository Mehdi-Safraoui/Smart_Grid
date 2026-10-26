# Module NLP : question en français → requête SPARQL

**Outils utilisés (à citer dans la présentation) :**
- **spaCy 3** avec le modèle français **fr_core_news_sm** : tokenisation, lemmatisation, étiquetage morpho-syntaxique (POS, morphologie).
- **spaCy PhraseMatcher** : reconnaissance des concepts de l'ontologie (classes, zones, individus) dans la phrase.
- **Expressions régulières (module `re`)** : comparateurs, nombres et unités (« plus de 50 MW »).
- **Gabarits SPARQL** : génération de la requête à partir des éléments reconnus.

Aucune API de LLM (OpenAI, Gemini…) n'est utilisée : tout tourne localement.

## Le pipeline en 4 étapes (`backend/app/nlp/pipeline.py`)

Exemple : **« Quelles sources produisent plus de 50 MW ? »**

### 1. Prétraitement (spaCy)
La phrase est découpée en tokens. Pour chacun, spaCy donne son lemme et sa catégorie grammaticale :
`Quelles/quel/ADJ · sources/source/NOUN · produisent/produire/VERB · plus · de · 50 · MW`.
On normalise ensuite le texte (minuscules, sans accents), pour que « Éolienne » et « eolienne » soient reconnus pareil.

### 2. Reconnaissance des entités
- Le **PhraseMatcher** compare la phrase, et sa version lemmatisée, au vocabulaire de l'ontologie (`vocabulaire.py`). Grâce aux lemmes, « sources » au pluriel retrouve « source » → **classe `SourceProduction`**.
- Les zones et les individus sont lus directement dans la base. Un individu ajouté depuis l'appli est donc reconnu tout de suite.
- Une expression régulière repère le comparateur, le nombre et l'unité : `plus de 50 MW` → **filtre `> 50`**, et l'unité MW désigne l'attribut **`puissanceMW`**.
- Si plusieurs expressions se chevauchent, on garde la plus longue : « centrale solaire » l'emporte sur « centrale ».

### 3. Détection de l'intention
| Indice dans la question | Intention |
|---|---|
| « combien », « nombre » | comptage → `COUNT` |
| comparateur + nombre | filtre → `FILTER` |
| « le plus / le moins » | superlatif → `ORDER BY … LIMIT 1` |
| verbe d'une relation (« alimente », « alimentés par ») | relation, avec le sens déduit de la voix (active ou passive) et de la position des entités par rapport au verbe |
| un individu seul | détail → toutes ses propriétés |
| sinon | liste |

### 4. Génération de la requête SPARQL
On remplit un gabarit avec les éléments trouvés :
```sparql
SELECT DISTINCT ?element ?puissanceMW ?zone WHERE {
  VALUES ?classe_element { sg:SourceProduction }
  ?element a/rdfs:subClassOf* ?classe_element .      # inclut toutes les sous-classes
  ?element sg:puissanceMW ?puissanceMW .
  FILTER(?puissanceMW > 50.0)
  OPTIONAL { ?element sg:estSitueDans ?zone }
}
ORDER BY DESC(?puissanceMW)
```
Le chemin `a/rdfs:subClassOf*` exploite la **hiérarchie de l'ontologie** : demander les
« sources » renvoie aussi les centrales solaires, les parcs éoliens et les sources fossiles.

La requête est ensuite exécutée par le serveur SPARQL. Le front affiche le résultat, avec
l'analyse détaillée (tokens, entités, intention, requête) dans « Voir l'analyse NLP ».

## Questions qui fonctionnent déjà
- Quelles sont les centrales solaires ?
- Quelles sources produisent plus de 50 MW ?
- Quelles centrales ont une puissance entre 10 et 100 MW ?
- Quelle est la source la plus puissante ?
- Liste les sources renouvelables à Tozeur
- Combien de bâtiments y a-t-il à Tunis ?
- Quels bâtiments consomment plus de 100 000 kWh ?
- Quels sont les gros consommateurs ?
- Quel stockage a la plus grande capacité ?
- Quelles lignes ont une tension supérieure à 100 kV ?
- Qui alimente l'usine de Sfax ?
- Quels bâtiments sont alimentés par le parc éolien ?
- Qu'alimente la batterie de Tozeur ?
- Donne-moi des infos sur Radès
- Qu'est-ce qu'il y a à Sfax ?

## Limites (à connaître si la prof pose la question)
- Le vocabulaire est défini à la main : un mot absent de `vocabulaire.py` n'est pas compris. C'est pour ça que chacun ajoute les synonymes de sa branche.
- Une seule relation par question.
- **Améliorations possibles :** un classifieur d'intentions entraîné (scikit-learn ou Hugging Face), une reconnaissance d'entités entraînée sur nos données, ou la correction des fautes de frappe.
