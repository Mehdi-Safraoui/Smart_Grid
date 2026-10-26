# ⚡ SmartGrid — Web sémantique

Mini-projet du module **Web sémantique** (5TWIN, 2026/2027) — Sujet 3 : *Énergie et Smart Grid*.
Équipe **Ctrl Alt Elite** : Mehdi Safraoui, Mohamed Elyess Zormati, Ahmed Amine Drira, Yassine Sayari.

Ontologie OWL du réseau électrique intelligent tunisien (production, stockage, consommation,
réseau), exploitée par une application web : CRUD en SPARQL, recherche, filtres, et un
**assistant NLP** qui traduit une question en français en requête SPARQL (spaCy, sans LLM).

## Architecture

```
 Navigateur (HTML/CSS/JS)          Backend Python (FastAPI)                Serveur SPARQL
 ─────────────────────────         ──────────────────────────             ───────────────────
 index.html   (assistant NLP) ──►  /api/ask        → nlp/pipeline.py  ──►  Apache Jena Fuseki
 production.html (CRUD)      ──►  /api/production → queries/*.py     ──►  (ou rdflib en local)
 stockage / consommation /   ──►  /api/stockage …                          chargé avec
 reseau.html                       /api/sparql (console)                    SmartGrid_inferred.owl
 console.html (SPARQL)
                         fetch() en JSON               SPARQL 1.1 (SELECT / INSERT / DELETE)
```

## Installation (une seule fois)

Prérequis : **Python 3.10+**, **Java** (uniquement pour le raisonneur HermiT), Docker (optionnel, pour Fuseki).

```bash
git clone <url-du-repo> && cd smartgrid-semantic
python -m venv .venv
# Windows : .venv\Scripts\activate      macOS / Linux : source .venv/bin/activate
pip install -r backend/requirements.txt
python -m spacy download fr_core_news_sm
```

## Lancer l'application

```bash
cd backend
uvicorn app.main:app --reload
```

- Application : **http://localhost:8000**
- Documentation de l'API (Swagger, pour tester chaque route) : **http://localhost:8000/docs**

Par défaut, le backend fonctionne en **mode local** : le graphe RDF est géré par rdflib, sans
serveur à installer. Pratique pour développer.

### Mode serveur Fuseki (à utiliser pour la soutenance)

```bash
docker compose up -d                 # lance Fuseki sur http://localhost:3030 (admin / admin)
python scripts/load_fuseki.py        # charge l'ontologie inférée
cp .env.example .env                 # active SPARQL_ENDPOINT=http://localhost:3030/smartgrid
cd backend && uvicorn app.main:app --reload
```

Sans Docker : télécharger *Apache Jena Fuseki* (jena.apache.org), puis lancer
`fuseki-server --update --mem /smartgrid` (Windows : `fuseki-server.bat`), et enfin `load_fuseki.py`.

`/api/health` indique le mode utilisé (`local` ou `fuseki`).

## Modifier l'ontologie

L'ontologie est générée par **`ontology/build_ontology.py`** : c'est la source de vérité.
Chacun ajoute ses individus **dans la section de sa branche**, puis :

```bash
python ontology/build_ontology.py    # régénère SmartGrid.owl + lance HermiT → SmartGrid_inferred.owl
```

- Le script s'arrête avec un message clair si HermiT détecte une incohérence.
- En mode local, supprimer `backend/data/` (ou appeler `POST /api/reset`) pour recharger l'ontologie.
- En mode Fuseki, relancer `python scripts/load_fuseki.py`.
- **Protégé sert à visualiser** (hiérarchie, OntoGraf, captures pour la présentation) : ouvrez
  `ontology/SmartGrid.owl`. Ne commitez pas de modification faite dans Protégé, sinon elle sera
  écrasée par le script.

## Tests

```bash
cd backend
python -m pytest -q
```

Avant chaque push, tous les tests doivent passer. Chacun ajoute les tests de sa branche dans
`backend/tests/test_api.py`.

## Organisation du code

```
ontology/
  build_ontology.py        classes, propriétés, axiomes, individus (chaque branche a sa section)
  reasoner.py              HermiT : cohérence + déductions → SmartGrid_inferred.owl
  SmartGrid.owl            ontologie (ouvrir dans Protégé)
  SmartGrid_inferred.owl   ontologie + déductions (chargée dans le serveur SPARQL)
backend/app/
  main.py                  application FastAPI (sert aussi le frontend)
  config.py                configuration (mode local / Fuseki)
  sparql_client.py         exécution des requêtes SPARQL (select / update)
  queries/                 requêtes SPARQL, un fichier par branche  ← production.py = MODÈLE
  routers/                 routes de l'API, un fichier par branche   ← production.py = MODÈLE
  nlp/vocabulaire.py       mots français ↔ concepts de l'ontologie (chaque branche complète)
  nlp/pipeline.py          pipeline NLP spaCy : question → SPARQL
backend/tests/test_api.py  tests automatiques
frontend/                  pages HTML + js/ (une page par branche)  ← production = MODÈLE
docs/REPARTITION.md        qui fait quoi, branche par branche, selon la grille
docs/NLP.md                explication du module NLP (pour la présentation)
```

## Travailler à plusieurs avec Git

Chacun travaille sur **sa propre branche Git** et ne modifie que les fichiers de sa branche
(voir `docs/REPARTITION.md`).

```bash
git checkout main && git pull                 # récupérer la dernière version
git checkout -b production                    # une seule fois (production / stockage / consommation / reseau)
# ... travail ...
(cd backend && python -m pytest -q)           # les tests doivent passer
git add . && git commit -m "Production : filtre par puissance"
git push -u origin production                 # puis ouvrir une Pull Request vers main sur GitHub
```

Pour récupérer le travail des autres pendant que vous développez :
`git checkout main && git pull && git checkout <ma-branche> && git merge main`.
