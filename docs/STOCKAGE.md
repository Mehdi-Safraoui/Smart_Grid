# Branche Stockage : Mohamed Elyess

Fiche de préparation pour la soutenance : ce qui a été fait, et comment l'expliquer.

## 1. Individus (2 pts) : `ontology/build_ontology.py`

| Individu | Type | Capacité | Zone | stockeEnergieDe | alimente |
|---|---|---|---|---|---|
| Batterie_Tozeur *(base)* | Batterie | 20 MWh | Tozeur | Centrale_Solaire_Tozeur | Usine_Sfax |
| Stockage_H2_SidiDaoud *(base)* | StockageHydrogene | 50 MWh | Nabeul | Parc_Eolien_SidiDaoud | Centre_Commercial_Tunis |
| **Batterie_Kairouan** | Batterie | 30 MWh | Kairouan | Centrale_Solaire_Kairouan | Centre_Commercial_Tunis |
| **Batterie_Tunis** | Batterie | 15 MWh | Tunis | Centrale_Gaz_Rades | Residence_ElMenzah |
| **Stockage_H2_Gabes** | StockageHydrogene | 120 MWh | Gabès | Centrale_Solaire_Tozeur | Centre_Commercial_Tunis |

Nouvelles zones : `Zone_Kairouan`, `Zone_Gabes`. HermiT : ✅ cohérente.

**Axiomes de la branche à savoir expliquer :**
- **Restriction** : `SystemeStockage ⊑ stockeEnergieDe some SourceProduction`. Tout stockage
  stocke l'énergie d'au moins une source. C'est pourquoi l'API refuse un stockage sans source (erreur 422).
- **Disjonction** : `Batterie ⊓ StockageHydrogene = ∅`. Un individu ne peut pas être les deux.
  Démo : bouton **« Tester une incohérence »** → HermiT répond « INCOHÉRENTE ».
- **Propriété fonctionnelle** : `capaciteStockageMWh` (une seule capacité par stockage).
- **Domaine / codomaine** : `stockeEnergieDe` va de `SystemeStockage` vers `SourceProduction`.

## 2. Requêtes SPARQL (4 pts) : `backend/app/queries/stockage.py`

| Fonction | Opération | Points à expliquer |
|---|---|---|
| `lister()` | SELECT | `OPTIONAL` (les attributs manquants ne cachent pas la ligne), `FILTER` min/max sur la capacité, `CONTAINS(LCASE(...))` pour la recherche, `GROUP_CONCAT` pour regrouper les sources et les bâtiments sur une ligne |
| `obtenir()` | SELECT | un seul individu (404 sinon) |
| `capacite_par_type()` | SELECT | agrégation `COUNT` / `SUM` / `AVG` + `GROUP BY` |
| `creer()` | INSERT DATA | on écrit `alimente` **et** `estAlimentePar` (le serveur SPARQL ne raisonne pas sur `owl:inverseOf`) |
| `modifier()` | DELETE / INSERT WHERE | l'`OPTIONAL` dans le WHERE permet la mise à jour même si l'ancienne valeur n'existe pas |
| `supprimer()` | DELETE WHERE ×2 | comme sujet **puis** comme objet (sinon `Usine_Sfax estAlimentePar …` resterait) |

Sécurité : tous les noms passent par `safe_id()`, ce qui empêche l'injection SPARQL (testé).

Console SPARQL : 3 requêtes stockage (capacité par technologie ; énergie stockée par source
renouvelable/fossile avec `BIND` + `COALESCE` ; batteries situées hors de la zone de leur source).

## 3. API : `backend/app/routers/stockage.py`

`GET /api/stockage` (filtres `type`, `zone`, `source`, `min_mwh`, `max_mwh`, `recherche`) ·
`GET /api/stockage/{nom}` · `POST` · `PUT /{nom}` · `DELETE /{nom}` · `GET /statistiques` ·
`POST /raisonner`. Toutes les routes sont testables dans Swagger : http://localhost:8000/docs

## 4. Interface : `frontend/stockage.html` + `js/stockage.js`

Statistiques par technologie, filtres (recherche, type, zone, source stockée, capacité min/max),
tableau avec Modifier / Supprimer, formulaire d'ajout/modification (plusieurs sources possibles),
panneau HermiT.

## 5. NLP (4 pts) : `backend/app/nlp/vocabulaire.py`

- Synonymes : accumulateur, batterie lithium-ion, hydrogène vert, pile à combustible, réserve d'énergie…
- Relations : `stocker` et `emmagasiner` → `stockeEnergieDe`
- Petite correction dans `pipeline.py` : le nom « stockage » commence comme le verbe « stocker ».
  On l'exclut, de la même manière que « alimentation » était déjà exclu pour « alimenter ».

Questions testées (`backend/tests/test_api.py`) :

| Question | Intention | Réponse |
|---|---|---|
| Quelle batterie stocke l'énergie de la centrale solaire de Tozeur ? | relation | Batterie_Tozeur |
| Quels stockages ont une capacité de plus de 30 MWh ? | filtre | Stockage_H2_Gabes, Stockage_H2_SidiDaoud |
| Quel stockage a la plus grande capacité ? | superlatif | Stockage_H2_Gabes |
| Combien de batteries y a-t-il ? | comptage | 3 |
| Qu'est-ce qui est stocké par le stockage hydrogène ? | relation (passif) | Centrale_Solaire_Tozeur, Parc_Eolien_SidiDaoud |
| Quelle batterie a la plus petite capacité ? | superlatif | Batterie_Tunis |
| Quels accumulateurs sont à Kairouan ? | liste (synonyme + zone) | Batterie_Kairouan |
| Combien de stockages y a-t-il à Nabeul ? | comptage + zone | 1 |

## 6. Scénario de démo (≈ 1 minute)

1. Page **Stockage** → formulaire : `Batterie_Sfax`, Batterie, 40 MWh, Zone Sfax, stocke
   *Centrale Solaire Tozeur*, alimente *Usine Sfax* → **Ajouter**. Elle apparaît dans la liste et
   les statistiques changent.
2. Filtre *Capacité min = 35* → elle reste affichée (FILTER SPARQL).
3. **Accueil** → assistant : « *Quelle batterie stocke l'énergie de la centrale solaire de Tozeur ?* »
   → Batterie_Sfax et Batterie_Tozeur. Ouvrir « Voir l'analyse NLP » pour montrer la requête générée.
4. « *Qui alimente l'usine de Sfax ?* » → la batterie apparaît aussi (relation inverse écrite par l'INSERT).
5. Retour sur **Stockage** → **Raisonner**, puis **Tester une incohérence** (voir ci-dessous).

## 7. Valeur ajoutée (2 pts) : le raisonneur HermiT dans l'appli (`backend/app/raisonnement.py`)

Le serveur SPARQL (Fuseki ou rdflib) **ne raisonne pas**. Le bouton **Raisonner** :
1. récupère toutes les données actuelles (y compris les ajouts du CRUD) ;
2. lance HermiT dessus avec owlready2 ;
3. compare avant / après et affiche les **nouvelles déductions** : classes définies
   (`GrosConsommateur`, `BatimentAlimenteRenouvelable`) et relations inverses ;
4. **Enregistrer les déductions** les écrit dans le serveur (INSERT DATA). L'assistant NLP
   les voit alors, par exemple pour « Quels sont les gros consommateurs ? » ;
5. **Tester une incohérence** déclare temporairement `Batterie_Tozeur` comme StockageHydrogene.
   HermiT détecte la violation de la disjonction, et rien n'est modifié dans la base.

Exemple : on ajoute un hôpital de 300 000 kWh alimenté par la centrale solaire de Tozeur.
HermiT déduit qu'il est **GrosConsommateur** et **BatimentAlimenteRenouvelable**, et qu'il
`estAlimentePar` la centrale.
