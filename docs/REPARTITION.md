# Répartition du travail

## Pourquoi on découpe par branche de l'ontologie

La grille de validation note **chaque étudiant individuellement sur tous les critères** :

| Critère | Points | Ce que la prof veut voir |
|---|---|---|
| Requêtes SPARQL | 4 | Des requêtes CRUD (SELECT, INSERT, UPDATE, DELETE) avec FILTER et recherche, que vous savez expliquer |
| Individus | 2 | Des individus réalistes, avec attributs et relations, cohérents selon HermiT |
| Scénario | 2 | Un cas d'usage déroulé en démo du début à la fin |
| API IA | 4 | Le module NLP : une question en français devient une requête SPARQL (spaCy, sans LLM) |
| Interfaces graphiques | 3 | Une page propre et fonctionnelle |
| Communication BE ↔ FE | 3 | Le front appelle l'API, l'API interroge le serveur SPARQL |
| Valeur ajoutée | 2 | Un bonus original |

Donc **chacun prend une branche de l'ontologie et la développe sur toute la chaîne** :
individus, SPARQL, API, page web, NLP, scénario, bonus. Comme ça, chacun a quelque chose à
montrer pour chaque critère.

| Membre | Branche | Classes |
|---|---|---|
| **Mehdi** | Production ✅ *(déjà faite : c'est le modèle)* | SourceProduction, SourceRenouvelable, CentraleSolaire, ParcEolien, SourceFossile |
| **Mohamed Elyess** | Stockage | SystemeStockage, Batterie, StockageHydrogene |
| **Ahmed Amine** | Consommation | BatimentConsommateur, BatimentResidentiel, BatimentCommercial, BatimentIndustriel, GrosConsommateur, BatimentAlimenteRenouvelable |
| **Yassine** | Réseau | InfrastructureReseau, LigneElectrique, LigneTransport, LigneDistribution, PosteTransformation, Zone |

La branche Production étant déjà faite, **Mehdi** s'occupe aussi de l'intégration : il relit
et fusionne les Pull Requests, fait tourner Fuseki pour la démo, met à jour la présentation et
écrit les tests NLP communs.

> ⚠️ À la soutenance, la prof peut interroger n'importe qui sur n'importe quelle partie.
> Chacun doit savoir expliquer **toute** la chaîne : ontologie → SPARQL → API → front → NLP.

---

## La checklist (la même pour chacun, sur sa branche)

Ouvrez à côté les fichiers *production* : ils montrent exactement quoi faire.

### 1. Individus (2 pts) — `ontology/build_ontology.py`
- [ ] Ajouter **au moins 3 individus réalistes** dans la section de votre branche, avec tous leurs attributs et relations (zone, et selon la branche : alimente, stockeEnergieDe, relie…).
- [ ] Si besoin, ajouter une zone (ex. `Zone_Kairouan`) dans la section *Localisation*.
- [ ] Lancer `python ontology/build_ontology.py` : HermiT doit afficher « ✅ cohérente ».
- [ ] Savoir expliquer une restriction ou une disjonction qui concerne votre branche, et la tester (ex. déclarer une batterie aussi en stockage hydrogène → HermiT signale une incohérence).

### 2. Requêtes SPARQL (4 pts) — `backend/app/queries/<branche>.py`
- [ ] `lister()` : ajouter les filtres numériques min / max sur votre attribut, et vos relations (OPTIONAL + GROUP_CONCAT, comme `alimente` dans production).
- [ ] `obtenir()` : un seul individu.
- [ ] `creer()` : **INSERT DATA**.
- [ ] `modifier()` : **DELETE / INSERT WHERE**.
- [ ] `supprimer()` : **DELETE WHERE** (comme sujet et comme objet).
- [ ] Ajouter 1 ou 2 requêtes « intelligentes » de votre branche dans la console (`frontend/js/console.js`), par exemple avec une agrégation COUNT / SUM / AVG + GROUP BY.

Deux règles techniques :
- **Une seule opération par appel `client.update()`** : le mode local n'accepte pas `op1 ; op2`.
- **Les propriétés inverses** (`alimente` / `estAlimentePar`) : écrivez les deux sens dans `INSERT DATA`, car le serveur SPARQL ne raisonne pas.
- Toujours passer les noms par `safe_id()` : c'est ce qui empêche l'injection SPARQL.

### 3. Backend (une partie des 3 pts communication) — `backend/app/routers/<branche>.py`
- [ ] Les routes `GET /{nom}`, `POST`, `PUT /{nom}`, `DELETE /{nom}`, avec des modèles Pydantic.
- [ ] Les tester dans Swagger (http://localhost:8000/docs).

### 4. Interface (3 pts) — `frontend/<branche>.html` + `frontend/js/<branche>.js`
- [ ] Formulaire de filtres : recherche, type, zone, min / max.
- [ ] Tableau avec boutons Modifier / Supprimer.
- [ ] Formulaire d'ajout et de modification.
- [ ] Retirer l'encadré jaune « À compléter ».

### 5. API IA / NLP (4 pts) — `backend/app/nlp/vocabulaire.py`
- [ ] Ajouter des synonymes pour vos classes (section de votre branche).
- [ ] Ajouter **votre relation** dans `RELATIONS` (voir le tableau plus bas).
- [ ] Faire marcher **au moins 5 questions** de votre branche et les ajouter comme tests dans `backend/tests/test_api.py`.
- [ ] Mettre vos meilleures questions dans **votre ligne d'exemples** de l'assistant (`frontend/js/chat.js`, objet `EXEMPLES`) : ce sont celles que vous poserez en démo.
- [ ] Savoir expliquer les 4 étapes du pipeline (voir `docs/NLP.md`) et les outils utilisés.

### 6. Scénario (2 pts)
- [ ] Préparer un mini-scénario de démo d'environ 1 minute (voir les exemples plus bas), et le répéter.

### 7. Valeur ajoutée (2 pts)
- [ ] Un bonus par personne (voir les propositions plus bas).

---

## Détails par membre

### Mehdi — Production (modèle) + intégration
- **Déjà fait :** individus de base, CRUD complet, page `production.html`, relation `alimente` dans le NLP.
- **À faire :**
  - ✅ 3 individus de plus : `Centrale_Solaire_Kairouan` (100 MW), `Parc_Eolien_Bizerte` (95 MW), `Centrale_Gaz_Sousse` (420 MW), avec les zones Kairouan, Bizerte et Sousse.
  - ✅ 10 questions NLP Production testées (`test_nlp_production*`).
  - Fuseki pour la soutenance (`docker compose up -d` puis `load_fuseki.py`).
  - Fusionner les Pull Requests et mettre à jour la présentation.
- **Scénario :** « J'ajoute depuis la page Production la centrale solaire de Gafsa (120 MW) qui alimente l'usine de Sfax → elle apparaît dans la liste → je demande à l'assistant *Qui alimente l'usine de Sfax ?* → elle sort avec les centrales de Tozeur et de Kairouan et la batterie. »
- **Valeur ajoutée :** ✅ tableau de bord en haut de la page Production : puissance installée, part renouvelable, graphiques par zone, par type et par bâtiment. Il repose sur des requêtes SPARQL d'agrégation (SUM, COUNT, GROUP BY) servies par `GET /api/production/tableau-de-bord`, et se met à jour après chaque ajout ou modification.

### Mohamed Elyess — Stockage
- **Individus :** par exemple `Batterie_Sfax`, `Batterie_Kairouan`, `Stockage_H2_Gabes`, chacun avec `capaciteStockageMWh`, `stockeEnergieDe` et `alimente`.
- **SPARQL :** CRUD complet, plus un filtre sur la capacité et l'affichage de la source stockée (`stockeEnergieDe`).
- **NLP :** dans `RELATIONS`, ajouter
  `"stocker": {"propriete": "stockeEnergieDe", "sujet": "SystemeStockage", "objet": "SourceProduction"}`.
  - Questions : « Quelle batterie stocke l'énergie de la centrale solaire de Tozeur ? », « Quels stockages ont une capacité de plus de 30 MWh ? », « Quel stockage a la plus grande capacité ? », « Combien de batteries y a-t-il ? », « Qu'est-ce qui est stocké par le stockage hydrogène ? »
- **Scénario :** « J'ajoute une batterie à Sfax qui stocke l'énergie de la centrale de Tozeur → je la retrouve par l'assistant. »
- **Valeur ajoutée :** l'inférence HermiT dans l'appli. Un bouton « Raisonner » appelle `ontology/reasoner.py` et affiche les déductions : classes définies, relations inverses, incohérences.

### Ahmed Amine — Consommation
- **Individus :** par exemple `Hopital_Sfax`, `Ecole_Tozeur`, `Hotel_Nabeul`, chacun avec `consommationKWh`, une zone et `estAlimentePar`.
- **SPARQL :** CRUD complet, plus un filtre sur la consommation, et la liste des **gros consommateurs** (consommation ≥ 100 000 kWh) et des **bâtiments alimentés en renouvelable**. Attention : ces deux classes sont déduites par HermiT. Pour un bâtiment ajouté depuis l'appli, utilisez un FILTER ou une sous-requête dans SPARQL.
- **NLP :** synonymes (immeuble, hôpital, école…) et un verbe de relation inverse si besoin.
  - Questions : « Quels bâtiments consomment plus de 100 000 kWh ? », « Quels sont les gros consommateurs ? », « Quel est le bâtiment qui consomme le plus ? », « Combien de bâtiments y a-t-il à Tunis ? », « Qui alimente le centre commercial ? »
- **Scénario :** « J'ajoute un hôpital à Sfax (300 000 kWh) alimenté par la centrale de Tozeur → il apparaît parmi les gros consommateurs. »
- **Valeur ajoutée :** une carte de la Tunisie (Leaflet) qui place les éléments par zone.

### Yassine — Réseau
- **Individus :** par exemple `Poste_Kairouan`, `Ligne_Kairouan_Sousse` (transport, 225 kV), `Ligne_Quartier_Sfax` (distribution, 0,4 kV), avec `relie` (au moins 2 éléments, sinon la restriction n'est pas respectée).
- **SPARQL :** CRUD complet, plus un filtre sur la tension, la liste des éléments reliés par une ligne (`relie`), et « transport ou distribution ».
- **NLP :** dans `RELATIONS`, ajouter
  `"relier": {"propriete": "relie", "sujet": "LigneElectrique", "objet": "ComposantSmartGrid"}` (et `"connecter"`).
  - Questions : « Quelles lignes ont une tension supérieure à 100 kV ? », « Quelles sont les lignes de distribution ? », « Qu'est-ce que relie la ligne Tozeur Sfax ? », « Combien de postes y a-t-il ? », « Qu'est-ce qu'il y a à Sfax ? »
- **Scénario :** « Je suis le parcours de l'énergie : centrale de Tozeur → ligne de transport 225 kV → poste de Sfax → ligne de distribution → usine. »
- **Valeur ajoutée :** une question vocale (Web Speech API du navigateur) ou un export CSV des résultats.

---

## Planning

| Jour | Objectif |
|---|---|
| J1 | Chacun clone le dépôt, installe, lance l'appli et les tests, lit `production` |
| J2 | Individus + requêtes SPARQL + routes de sa branche |
| J3 | Page front + NLP de sa branche + tests |
| J4 | Scénario + valeur ajoutée + Pull Request vers main. Mehdi fusionne et met à jour la présentation |
| Veille | Répétition complète sur Fuseki, chacun présente sa partie et sait expliquer le reste |
