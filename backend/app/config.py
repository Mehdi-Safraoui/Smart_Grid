"""Configuration du backend (modifiable par variables d'environnement ou fichier .env)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # racine du dépôt

# Lecture du fichier .env à la racine (s'il existe)
_env = ROOT / ".env"
if _env.exists():
    for _ligne in _env.read_text(encoding="utf-8").splitlines():
        if "=" in _ligne and not _ligne.lstrip().startswith("#"):
            _cle, _val = _ligne.split("=", 1)
            os.environ.setdefault(_cle.strip(), _val.strip())
ONTOLOGY_FILE = ROOT / "ontology" / "SmartGrid_inferred.owl"
LOCAL_STORE = ROOT / "backend" / "data" / "store.ttl"

# Mode serveur : URL du dataset Fuseki, ex. http://localhost:3030/smartgrid
# Laisser vide pour utiliser le mode local (rdflib, aucun serveur à installer).
SPARQL_ENDPOINT = os.getenv("SPARQL_ENDPOINT", "").rstrip("/")
FUSEKI_USER = os.getenv("FUSEKI_USER", "admin")
FUSEKI_PASSWORD = os.getenv("FUSEKI_PASSWORD", "admin")

NS = "http://www.semanticweb.org/smartgrid/ontologie#"

PREFIXES = f"""PREFIX sg:   <{NS}>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
"""
