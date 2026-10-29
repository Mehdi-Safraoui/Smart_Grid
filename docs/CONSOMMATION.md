# Branche Consommation (Ahmed Amine)

Bâtiments résidentiels, commerciaux (tertiaire) et industriels, et les deux classes définies
**GrosConsommateur** et **BatimentAlimenteRenouvelable**.

| Critère | Où le montrer |
|---|---|
| Individus | `ontology/build_ontology.py`, section *Consommation* |
| Axiomes / HermiT | `ontology/test_incoherence_consommation.py` |
| SPARQL CRUD | `backend/app/queries/consommation.py` |
| API | `backend/app/routers/consommation.py` → Swagger `/docs`, tag *Consommation* |
| Interface | `frontend/consommation.html` + `frontend/js/consommation.js` |
| NLP | `backend/app/nlp/vocabulaire.py` (synonymes, verbes) + intention *agrégat* dans `pipeline.py` |
| Requêtes de la console | `frontend/js/console.js` (4 requêtes « Consommation : … ») |
| Tests | `backend/tests/test_api.py`, section *CONSOMMATION* |
| Valeur ajoutée | carte Leaflet de la Tunisie + bilan par zone + reclassement SPARQL |

## 1. Individus

| Individu | Classe | Consommation | Alimenté par | Zone | Gros ? | Renouvelable ? |
|---|---|---|---|---|---|---|
| Usine_Sfax | BatimentIndustriel | 900 000 kWh | Centrale_Solaire_Tozeur, Batterie_Tozeur | Sfax | ✅ | ✅ |
| Centre_Commercial_Tunis | BatimentCommercial | 250 000 kWh | Parc_Eolien_SidiDaoud, Stockage_H2_SidiDaoud | Tunis | ✅ | ✅ |
| **Hotel_Nabeul** | BatimentCommercial | 180 000 kWh | Parc_Eolien_SidiDaoud | Nabeul | ✅ | ✅ |
| **Usine_Textile_Nabeul** | BatimentIndustriel | 150 000 kWh | Stockage_H2_SidiDaoud | Nabeul | ✅ | ❌ |
| **Cite_Ennasr_Tunis** | BatimentResidentiel | 45 000 kWh | Centrale_Gaz_Rades | Tunis | ❌ | ❌ |
| **Residence_Tozeur** | BatimentResidentiel | 30 000 kWh | Centrale_Solaire_Tozeur, Batterie_Tozeur | Tozeur | ❌ | ✅ |
| Residence_ElMenzah | BatimentResidentiel | 12 000 kWh | Centrale_Gaz_Rades | Tunis | ❌ | ❌ |

En gras : les 4 individus ajoutés. Ils ont été choisis pour couvrir **les 4 combinaisons** des
deux classes définies. Point subtil à savoir expliquer : `Usine_Textile_Nabeul` est alimentée
par un **stockage hydrogène**, qui n'est **pas** une `SourceRenouvelable` (c'est un
`SystemeStockage`, disjoint de `SourceProduction`). HermiT ne la classe donc pas en
« alimentée en renouvelable », même si l'hydrogène stocke de l'éolien.

Le tertiaire (hôtel, hôpital, école) est rangé dans `BatimentCommercial` : l'ontologie classe
les bâtiments selon leur usage en trois catégories seulement.

Dans le code on écrit `estSitueDans` et `alimente` côté source (`eolien.alimente = [com, hotel]`).
HermiT déduit l'inverse `estAlimentePar` (`owl:inverseOf`), et `reasoner.py` l'écrit dans
`SmartGrid_inferred.owl` pour que SPARQL le voie.

### Axiomes de la branche (à savoir expliquer)

- **Classes définies** (`EquivalentTo`), remplies automatiquement par HermiT :
  - `GrosConsommateur ≡ BatimentConsommateur ⊓ ∃consommationKWh.float[≥ 100000]`
  - `BatimentAlimenteRenouvelable ≡ BatimentConsommateur ⊓ ∃estAlimentePar.SourceRenouvelable`

  Différence avec une sous-classe simple : on ne dit jamais « Hotel_Nabeul est un gros
  consommateur ». HermiT le **déduit** de sa consommation (condition nécessaire **et** suffisante).
- **Restriction** `BatimentConsommateur ⊑ ∃estAlimentePar.(SourceProduction ⊔ SystemeStockage)`.
  HermiT raisonne en **monde ouvert** : un bâtiment sans fournisseur ne le gêne pas (il suppose
  qu'un fournisseur inconnu existe). C'est donc l'**API** qui fait respecter la règle : elle refuse
  un bâtiment sans fournisseur (erreur 400).
- **Disjonction** `BatimentResidentiel ⊓ BatimentCommercial ⊓ BatimentIndustriel = ∅`.
- **Propriété fonctionnelle** `consommationKWh` : une seule valeur par bâtiment.
- **Codomaine** de `estAlimentePar` : `SourceProduction ⊔ SystemeStockage`.

Démonstration avec HermiT (Java nécessaire) :
```bash
python ontology/test_incoherence_consommation.py
# ✅ Bâtiment à la fois résidentiel et industriel : incohérente, comme attendu
# ✅ Bâtiment avec deux consommations : incohérente, comme attendu
# ✅ Bâtiment alimenté par une zone : incohérente, comme attendu
# ✅ Hôpital de Sfax (300 000 kWh, solaire) classé par HermiT dans : BatimentAlimenteRenouvelable, BatimentCommercial, GrosConsommateur
```
Pourquoi « alimenté par une zone » est incohérent : le codomaine de `estAlimentePar` oblige
HermiT à déduire que la zone est une source ou un stockage, donc un `ComposantSmartGrid`. Or
`ComposantSmartGrid` et `Zone` sont disjointes → contradiction.

Le script ajoute les erreurs **en mémoire seulement** : `SmartGrid.owl` n'est pas modifié.

## 2. Requêtes SPARQL (`queries/consommation.py`)

| Fonction | Requête | Points à expliquer |
|---|---|---|
| `lister()` | `SELECT … GROUP BY` | `VALUES ?type` (les 3 classes instanciables), `OPTIONAL`, `GROUP_CONCAT` pour la liste des fournisseurs, `FILTER(?consommation >= …)`, `CONTAINS(LCASE(STR(?x)))` pour la recherche, et deux colonnes calculées avec `BIND(IF(…, 1, 0))` : `?gros` (seuil) et `?renouvelable` (`EXISTS { … SourceRenouvelable }`) |
| `obtenir()` | `SELECT` | un seul bâtiment (404 sinon) |
| `creer()` | `INSERT DATA` | écrit **les deux sens** `estAlimentePar` / `alimente` (le serveur ne raisonne pas sur `owl:inverseOf`), vérifie les fournisseurs (codomaine + au moins un) |
| `modifier()` | `DELETE / INSERT WHERE` | l'`OPTIONAL` dans le `WHERE` permet de modifier même si l'ancienne valeur n'existe pas ; la liste des fournisseurs est remplacée (2 `DELETE WHERE` pour les deux sens, puis `INSERT DATA`) |
| `supprimer()` | `DELETE WHERE` ×2 | comme sujet, puis comme objet (sinon la source garderait `alimente` vers un bâtiment disparu) |
| `gros_consommateurs()` | `SELECT … FILTER` | la classe définie réécrite en SPARQL, avec un seuil réglable |
| `alimentes_renouvelable()` | `SELECT … GROUP BY` | jointure bâtiment → source + `a/rdfs:subClassOf* sg:SourceRenouvelable` |
| `par_zone()` | `COUNT / SUM / AVG + GROUP BY` | bilan par zone, `COALESCE` pour une consommation absente |
| `carte()` | `SELECT DISTINCT` | tous les composants avec leur branche et leur zone |
| `classer()` | `DELETE WHERE` + `INSERT … WHERE` | voir ci-dessous |

### Le problème des classes déduites (question probable de la prof)

HermiT a classé les individus **de l'ontologie**. Mais le serveur SPARQL (Fuseki ou rdflib) **ne
raisonne pas** : un hôpital ajouté depuis l'appli n'aurait jamais le type `GrosConsommateur`.
Deux solutions, utilisées toutes les deux :

1. **À la lecture**, `lister()` recalcule `?gros` et `?renouvelable` par `FILTER` / `EXISTS` :
   le tableau est toujours juste.
2. **À l'écriture**, `classer()` traduit les définitions OWL en **règles SPARQL** et les applique
   après chaque ajout / modification :
   ```sparql
   DELETE WHERE { ?b a sg:GrosConsommateur }
   INSERT { ?b a sg:GrosConsommateur }
   WHERE  { ?b a/rdfs:subClassOf* sg:BatimentConsommateur ;
               sg:consommationKWh ?c .
            FILTER(?c >= 100000) }
   ```
   (même chose pour `BatimentAlimenteRenouvelable` avec `FILTER EXISTS`). Ainsi l'assistant NLP,
   qui interroge la classe `sg:GrosConsommateur`, trouve aussi les bâtiments ajoutés.
   Le bouton **« Reclasser (règles SPARQL) »** de la page le déclenche à la main (par exemple
   après qu'une autre branche a modifié une source).

### Requêtes de la console (`console.js`)
- total / moyenne / max par type de bâtiment (`COUNT`, `SUM`, `AVG`, `MAX`, `GROUP BY`) ;
- gros consommateurs par `FILTER`, sans raisonneur ;
- bâtiments sans aucune source renouvelable (`FILTER NOT EXISTS`) ;
- part de chaque zone dans la consommation totale (deux **sous-requêtes**).

Piège évité : dans le graphe inféré, un bâtiment a plusieurs types (`BatimentIndustriel`,
`BatimentConsommateur`, `GrosConsommateur`…). Le chemin `a/rdfs:subClassOf*` peut donc renvoyer
plusieurs fois le même bâtiment et fausser un `SUM`. D'où les `DISTINCT`, `VALUES ?type`, ou le
passage par `sg:consommationKWh` seul (son domaine est `BatimentConsommateur`).

## 3. API (`routers/consommation.py`)

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/consommation` | liste + filtres `type`, `zone`, `min_kwh`, `max_kwh`, `recherche`, `alimente_par`, `gros`, `renouvelable` |
| GET | `/api/consommation/{nom}` | un bâtiment |
| POST | `/api/consommation` | ajout (modèle Pydantic `BatimentIn`) |
| PUT | `/api/consommation/{nom}` | modification (`BatimentUpdate`) |
| DELETE | `/api/consommation/{nom}` | suppression |
| GET | `/api/consommation/gros-consommateurs?seuil=` | classe définie, seuil réglable |
| GET | `/api/consommation/renouvelables` | classe définie + sources vertes |
| GET | `/api/consommation/par-zone` | agrégats par zone |
| GET | `/api/consommation/carte` | données de la carte |
| GET | `/api/consommation/fournisseurs` | sources et stockages (pour le formulaire) |
| POST | `/api/consommation/classer` | applique les règles SPARQL des classes définies |

Codes d'erreur : 400 (identifiant invalide → protection contre l'injection SPARQL par `safe_id()`,
type inconnu, fournisseur absent ou invalide), 404 (bâtiment introuvable), 409 (doublon), 422
(consommation ≤ 0, validée par Pydantic).

## 4. Interface (`consommation.html`)
- **Indicateurs** : nombre de bâtiments, consommation totale, gros consommateurs, part alimentée en renouvelable.
- **Filtres** : recherche, type, zone, fournisseur, consommation min / max, gros consommateur, renouvelable.
- **Tableau** avec badges des classes déduites, boutons Modifier / Supprimer.
- **Formulaire** d'ajout / modification, avec choix multiple des fournisseurs (Ctrl + clic).
- **Carte Leaflet** (valeur ajoutée) : un cercle par zone, dont la taille dépend de la
  consommation et la couleur de la part de bâtiments alimentés en renouvelable. Le clic affiche
  tous les éléments de la zone, toutes branches confondues. À côté, le bilan par zone (`par_zone()`).
  Les zones de l'ontologie n'ont pas de coordonnées : elles sont dans `COORDONNEES` (JS).

Communication front ↔ back : chaque action appelle `api()` (`js/api.js`, `fetch` en JSON) →
route FastAPI → fonction de `queries/consommation.py` → requête SPARQL sur Fuseki / rdflib.

## 5. NLP
- **Synonymes** ajoutés : immeuble, appartement, villa, cité, foyer (résidentiel) ; hôtel,
  hôpital, clinique, école, supermarché, bureau, tertiaire (commercial) ; fabrique, atelier,
  cimenterie (industriel) ; bâtiment énergivore (gros consommateur) ; bâtiment écologique (vert).
- « centre commercial » n'est plus un synonyme de classe : sinon « le centre commercial »
  désignerait **tous** les bâtiments commerciaux (hôtel compris). Le mot « centre » devient
  l'alias de l'individu `Centre_Commercial_Tunis`.
- **Verbes** : `dépendre` → `estAlimentePar` (« Quels bâtiments dépendent de la centrale de
  Radès ? ») et `approvisionner` → `alimente`.
- **Nouvelle intention « agrégat »** (`pipeline.py`) : « total / somme » → `SUM`, « moyenne » →
  `AVG`. Les mots déjà reconnus comme entité sont ignorés : « moyenne tension » reste une classe.
- **Correction** : « Qu'est-ce **qui** alimente l'usine textile ? » n'inverse plus le sens de la
  relation (seul « Qu'est-ce **que** … » le fait).

Questions testées (`test_nlp_consommation`, `test_nlp_consommation_agregats`) :
- Quels bâtiments consomment plus de 100 000 kWh ?
- Quels sont les gros consommateurs ?
- Quel est le bâtiment qui consomme le plus ? / Quel bâtiment consomme le moins ?
- Combien de bâtiments y a-t-il à Tunis ? / Combien de gros consommateurs y a-t-il ?
- Qui alimente le centre commercial ? / Qui alimente l'hôtel de Nabeul ?
- Qu'est-ce qui alimente l'usine textile ?
- Quels sont les bâtiments verts ?
- Quels bâtiments dépendent de la centrale de Radès ?
- Quels immeubles sont à Tozeur ?
- Quels hôtels consomment entre 100 000 et 200 000 kWh ?
- Quelle est la consommation totale des bâtiments à Tunis ? → `SUM` = 307 000 kWh
- Quelle est la consommation moyenne des bâtiments industriels ? → `AVG` = 525 000 kWh

## 6. Scénario de démo (≈ 1 min)

1. Page **Consommation** : « Voici les 7 bâtiments ; les badges *Gros consommateur* et
   *Renouvelable* sont des classes **déduites** par HermiT, pas saisies. »
2. Formulaire : `Hopital_Sfax`, Commercial, **300 000 kWh**, zone Sfax, alimenté par
   **Centrale Solaire Tozeur** → *Ajouter*. Le tableau affiche les deux badges, les indicateurs
   passent à 8 bâtiments / 5 gros consommateurs, et le cercle de Sfax grossit sur la carte.
3. Filtre *Gros consommateur = Oui* + zone Sfax → l'usine et l'hôpital.
4. **Accueil**, assistant : « Quels sont les gros consommateurs ? » → l'hôpital apparaît (grâce
   aux règles SPARQL de `classer()`), puis « Qui alimente l'hôpital de Sfax ? » → la centrale de Tozeur.
   Ouvrir « Voir l'analyse NLP » pour montrer tokens, entités et requête générée.
5. *Modifier* l'hôpital : 50 000 kWh, alimenté par la centrale de Radès → les deux badges disparaissent.
6. *Supprimer* → il disparaît aussi de la colonne « Alimente » de la centrale (page Production).

Avant la démo : `POST /api/reset` (mode local) ou `python scripts/load_fuseki.py` (Fuseki).

## 7. Commandes

```bash
python ontology/build_ontology.py                  # régénère l'ontologie + HermiT
python ontology/test_incoherence_consommation.py   # démo des axiomes
cd backend && python -m pytest -q                  # tests
```
HermiT a besoin de Java. Sans Java installé, on peut utiliser celui fourni avec IntelliJ :
`set PATH=C:\Program Files\JetBrains\IntelliJ IDEA 2025.2.2\jbr\bin;%PATH%` (cmd) avant la commande.
