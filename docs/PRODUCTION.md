# Branche Production (Mehdi)

Sources de production d'énergie : centrales solaires, parcs éoliens et sources fossiles.
Mehdi s'occupe aussi de l'intégration (fusion des branches, Fuseki, présentation).

| Critère de la grille | Où le montrer |
|---|---|
| Individus | `ontology/build_ontology.py`, section *Production* |
| Axiomes / HermiT | `ontology/test_incoherence_production.py` |
| SPARQL CRUD | `backend/app/queries/production.py` |
| SPARQL agrégations | `tableau_de_bord()` dans `queries/production.py` + 3 requêtes de la console |
| API | `backend/app/routers/production.py` → Swagger `/docs`, tag *Production* |
| Interface | `frontend/production.html` + `frontend/js/production.js` |
| NLP | intention **regroupement** dans `backend/app/nlp/pipeline.py` (`_regroupement`) + `vocabulaire.py` |
| Tests | `backend/tests/test_api.py`, sections *PRODUCTION*, *NLP PRODUCTION* et *NLP REGROUPEMENT* |
| Valeur ajoutée | tableau de bord (`frontend/js/dashboard.js`, `frontend/css/dashboard.css`) |

## 1. Classes et individus

```
SourceProduction
├── SourceRenouvelable          (disjointe de SourceFossile)
│   ├── CentraleSolaire         (disjointe de ParcEolien)
│   └── ParcEolien
└── SourceFossile
```
Attribut : `puissanceMW` (fonctionnel). Relations : `estSitueDans` (fonctionnelle), `alimente`
(inverse : `estAlimentePar`).

| Individu | Classe | Puissance | Zone | Alimente |
|---|---|---|---|---|
| Centrale_Solaire_Tozeur | CentraleSolaire | 10 MW | Tozeur | Usine_Sfax, Residence_Tozeur |
| **Centrale_Solaire_Kairouan** | CentraleSolaire | 100 MW | Kairouan | Usine_Sfax |
| Parc_Eolien_SidiDaoud | ParcEolien | 54 MW | Nabeul | Centre_Commercial_Tunis, Hotel_Nabeul |
| **Parc_Eolien_Bizerte** | ParcEolien | 95 MW | Bizerte | Hotel_Nabeul |
| Centrale_Gaz_Rades | SourceFossile | 450 MW | Tunis | Residence_ElMenzah, Cite_Ennasr_Tunis |
| **Centrale_Gaz_Sousse** | SourceFossile | 420 MW | Sousse | Centre_Commercial_Tunis |

En gras : les 3 individus ajoutés (puissances indicatives, inspirées d'installations tunisiennes).
Total : 1 129 MW, dont 259 MW renouvelables (22,9 %).

## 2. Axiomes vérifiés par HermiT

`python ontology/test_incoherence_production.py` ajoute en mémoire un fait interdit et
vérifie que HermiT déclare l'ontologie incohérente :

| Fait ajouté | Axiome qui le refuse |
|---|---|
| Centrale de Kairouan à la fois solaire et éolienne | `DisjointClasses(CentraleSolaire, ParcEolien)` |
| Centrale solaire de Tozeur déclarée aussi fossile | `CentraleSolaire ⊑ SourceRenouvelable` + `DisjointClasses(SourceRenouvelable, SourceFossile)` |
| Radès avec 450 MW **et** 500 MW | `puissanceMW` est fonctionnelle |
| Parc de Bizerte qui « alimente » la zone de Tunis | codomaine de `alimente` = `BatimentConsommateur`, disjoint de `Zone` |
| Centrale de Sousse qui « stocke » de l'énergie | domaine de `stockeEnergieDe` = `SystemeStockage`, disjoint de `SourceProduction` |

Puis un cas cohérent : une école de 150 000 kWh alimentée par la centrale de Kairouan est
**classée automatiquement** `GrosConsommateur` et `BatimentAlimenteRenouvelable`, et HermiT
déduit la relation inverse `estAlimentePar`.

## 3. Requêtes SPARQL

**CRUD** (`queries/production.py`) :
- `lister()` : `SELECT` + `OPTIONAL` + `GROUP_CONCAT` (bâtiments alimentés), filtres `FILTER` sur la
  puissance min/max, le type (`a/rdfs:subClassOf*`), la zone, et recherche `CONTAINS(LCASE(STR(?s)))`.
- `creer()` : `INSERT DATA`. On écrit `alimente` **et** `estAlimentePar`, parce que le serveur
  SPARQL ne raisonne pas sur `owl:inverseOf`.
- `modifier()` : `DELETE { ancienne valeur } INSERT { nouvelle } WHERE { OPTIONAL {…} }`.
- `supprimer()` : deux `DELETE WHERE` (l'individu comme sujet, puis comme objet).
- Tous les noms passent par `safe_id()`, ce qui empêche l'injection SPARQL.

**Agrégations** (tableau de bord, `GET /api/production/tableau-de-bord`) :
1. puissance et nombre de sources par catégorie (`VALUES` + `SUM` + `COUNT` + `GROUP BY`) ;
2. puissance par zone, séparée renouvelable / fossile ;
3. puissance par type de source ;
4. puissance renouvelable reçue par chaque bâtiment (en suivant la relation `alimente`).

**Console** (3 requêtes) :
- part renouvelable par zone (`IF` dans `SUM`, `EXISTS`, `ROUND`) ;
- sources dont l'énergie n'est stockée nulle part (`FILTER NOT EXISTS`) ;
- sources renouvelables plus puissantes que la moyenne (sous-requête `AVG`).

## 4. API

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/production?type=&zone=&min_mw=&max_mw=&recherche=` | liste + filtres |
| GET | `/api/production/types` | types instanciables |
| GET | `/api/production/tableau-de-bord` | indicateurs agrégés |
| GET | `/api/production/{nom}` | une source |
| POST | `/api/production` | ajout |
| PUT | `/api/production/{nom}` | modification (puissance, zone) |
| DELETE | `/api/production/{nom}` | suppression |

## 5. NLP : l'intention « regroupement »

Mon ajout au moteur NLP. Quand la question contient « par zone », « par type », « pour chaque
zone » ou « répartition », la requête générée regroupe les résultats (`GROUP BY`) :

| Question | Requête générée |
|---|---|
| Quelle est la puissance installée par zone ? | `SUM(?puissanceMW)` + `COUNT` … `GROUP BY ?zone` |
| Combien de sources par type ? | `COUNT` … `GROUP BY ?type` |
| Quelle est la puissance moyenne des sources par type ? | `AVG(?puissanceMW)` … `GROUP BY ?type` |
| Combien de sources renouvelables par zone ? | `COUNT` … `GROUP BY ?zone`, limité à `SourceRenouvelable` |
| Quelle est la consommation totale par zone ? | `SUM(?consommationKWh)` … `GROUP BY ?zone` |

Comment ça marche :
- **Détection :** expressions de `REGROUPEMENTS` dans `vocabulaire.py`, cherchées dans la question normalisée.
- **Mesure :** on ajoute `SUM` (ou `AVG` si « moyenne ») seulement si un attribut est demandé (« puissance », « MW », « consommation »…). Sinon, on compte seulement.
- **Sous-requête `SELECT DISTINCT` :** un élément qui a plusieurs types (un bâtiment industriel et gros consommateur, par exemple) n'est compté qu'une seule fois.
- **Regroupement par type :** on ne garde que les classes « feuilles » (`TYPES_FEUILLES`), pour qu'un élément tombe dans un seul groupe.

J'ai aussi rendu la reconnaissance des entités plus robuste au pluriel (« sources
renouvelables » → `SourceRenouvelable`), au profit de toutes les branches.

## 6. Valeur ajoutée : le tableau de bord

En haut de la page Production :
- 3 indicateurs : puissance installée, part renouvelable (avec une jauge) et puissance fossile à remplacer ;
- 3 graphiques : par zone, par type de source, et énergie verte reçue par bâtiment ;
- une infobulle au survol et un tableau « Voir les données » sous chaque graphique.

Les graphiques sont faits en HTML/CSS, sans bibliothèque externe, donc ils fonctionnent sans
Internet. Ils se mettent à jour après chaque ajout, modification ou suppression.

## 7. Scénario de démo (≈ 2 min)

1. **Page Production :** le tableau de bord affiche **1 129 MW**, dont **22,9 %** renouvelables.
2. **Ajout :** `Centrale_Solaire_Sfax`, centrale solaire de **120 MW**, zone Sfax, qui alimente `Usine_Sfax`, puis **Ajouter**.
3. **Mise à jour :** elle apparaît dans la liste, et le tableau de bord passe à **1 249 MW**, dont **30,3 %** renouvelables.
4. **Filtre :** puissance min 100 → Radès, Sousse, Sfax et Kairouan.
5. **Assistant (accueil) :**
   - *« Qui alimente l'usine de Sfax ? »* → la nouvelle centrale sort, avec Tozeur, Kairouan et la batterie. C'est la relation inverse, écrite dans les deux sens.
   - *« Quelle est la puissance installée par zone ? »* → Sfax apparaît avec 120 MW. Ouvrir « Voir l'analyse NLP » pour montrer les tokens, les entités et le `GROUP BY`.
6. **Console SPARQL :** lancer *« Production : part renouvelable par zone »*.
7. **Axiomes (terminal) :** `python ontology/test_incoherence_production.py`.
8. **Remise à zéro avant de passer la main :** supprimer `Centrale_Solaire_Sfax`.

## 8. Questions possibles de la prof

- **« Pourquoi écrire `alimente` et `estAlimentePar` dans l'INSERT ? »** Fuseki et rdflib ne
  font pas de raisonnement OWL. Sans les deux sens, la question « qui alimente ce bâtiment ? »
  ne trouverait pas la nouvelle source. HermiT, lui, déduit le sens inverse tout seul.
- **« Pourquoi une sous-requête DISTINCT dans les regroupements ? »** Le chemin
  `a/rdfs:subClassOf*` peut trouver un même élément par plusieurs de ses types. Sans `DISTINCT`,
  sa valeur serait additionnée plusieurs fois.
- **« Où est le NLP ? »** spaCy (`fr_core_news_sm`) fait la tokenisation, les lemmes et la
  catégorie des mots. Le `PhraseMatcher` reconnaît les entités de l'ontologie, des expressions
  régulières repèrent les nombres et les unités, et un gabarit génère la requête SPARQL. Aucune
  API de LLM n'est utilisée.
