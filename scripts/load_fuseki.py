"""
Charge l'ontologie inférée dans le serveur Fuseki (remplace le contenu existant).

    python scripts/load_fuseki.py                       # http://localhost:3030/smartgrid
    python scripts/load_fuseki.py http://hote:3030/smartgrid

À relancer après chaque modification de l'ontologie (build_ontology.py ou Protégé + reasoner.py).
"""
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
FICHIER = ROOT / "ontology" / "SmartGrid_inferred.owl"
DATASET = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3030/smartgrid").rstrip("/")

r = requests.put(f"{DATASET}/data?default", data=FICHIER.read_bytes(),
                 headers={"Content-Type": "application/rdf+xml"}, auth=("admin", "admin"))
if r.ok:
    n = requests.post(f"{DATASET}/query", data={"query": "SELECT (COUNT(*) AS ?n) WHERE {?s ?p ?o}"},
                      headers={"Accept": "application/sparql-results+json"})
    print(f"✅ Ontologie chargée dans {DATASET} "
          f"({n.json()['results']['bindings'][0]['n']['value']} triplets)")
else:
    sys.exit(f"❌ Échec ({r.status_code}) : {r.text[:300]}\n"
             "Fuseki est-il lancé ? (docker compose up -d)")
