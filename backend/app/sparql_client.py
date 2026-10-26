"""
Client SPARQL unique utilisé par tout le backend.

Deux modes, même interface (select / update) :
  * Serveur Fuseki  : si la variable SPARQL_ENDPOINT est définie (mode de la soutenance).
  * Local (rdflib)  : sinon. Le graphe est chargé depuis l'ontologie inférée et
                      sauvegardé dans backend/data/store.ttl après chaque modification.
"""
from __future__ import annotations

import threading
from decimal import Decimal

from .config import (FUSEKI_PASSWORD, FUSEKI_USER, LOCAL_STORE, NS, ONTOLOGY_FILE,
                     PREFIXES, SPARQL_ENDPOINT)


def short(value: str) -> str:
    """http://...ontologie#Usine_Sfax  ->  Usine_Sfax"""
    return value.split("#")[-1] if value.startswith(NS) or "#" in value else value


def _convert(binding_value) -> object:
    """Convertit une valeur SPARQL en valeur Python lisible par le front."""
    if isinstance(binding_value, dict):                      # format JSON (Fuseki)
        v, t, dt = binding_value["value"], binding_value["type"], binding_value.get("datatype", "")
        if t == "uri":
            return short(v)
        if dt.endswith(("#decimal", "#double", "#float")):
            return float(v)
        if dt.endswith("#integer"):
            return int(v)
        return v
    # objets rdflib (mode local)
    from rdflib import Literal, URIRef
    if isinstance(binding_value, URIRef):
        return short(str(binding_value))
    if isinstance(binding_value, Literal):
        py = binding_value.toPython()
        return float(py) if isinstance(py, Decimal) else py
    return None if binding_value is None else str(binding_value)


class SparqlClient:
    def __init__(self) -> None:
        self.mode = "fuseki" if SPARQL_ENDPOINT else "local"
        self._lock = threading.Lock()
        if self.mode == "local":
            self._load_local()

    # ------------------------------------------------------------------ local
    def _load_local(self, reset: bool = False) -> None:
        from rdflib import Graph
        self.graph = Graph()
        if LOCAL_STORE.exists() and not reset:
            self.graph.parse(LOCAL_STORE, format="turtle")
        else:
            self.graph.parse(ONTOLOGY_FILE)
            self._save_local()

    def _save_local(self) -> None:
        LOCAL_STORE.parent.mkdir(parents=True, exist_ok=True)
        self.graph.serialize(LOCAL_STORE, format="turtle")

    # ------------------------------------------------------------------ API
    def select(self, query: str) -> list[dict]:
        """Exécute un SELECT et renvoie une liste de dictionnaires {variable: valeur}."""
        full = PREFIXES + query
        if self.mode == "fuseki":
            from SPARQLWrapper import JSON, SPARQLWrapper
            sw = SPARQLWrapper(f"{SPARQL_ENDPOINT}/query")
            sw.setQuery(full)
            sw.setReturnFormat(JSON)
            data = sw.query().convert()
            return [{k: _convert(v) for k, v in row.items()}
                    for row in data["results"]["bindings"]]
        with self._lock:
            result = self.graph.query(full)
            return [{str(var): _convert(row[var]) for var in result.vars if row[var] is not None}
                    for row in result]

    def update(self, query: str) -> None:
        """Exécute une requête de mise à jour (INSERT / DELETE)."""
        full = PREFIXES + query
        if self.mode == "fuseki":
            from SPARQLWrapper import POST, SPARQLWrapper
            sw = SPARQLWrapper(f"{SPARQL_ENDPOINT}/update")
            sw.setCredentials(FUSEKI_USER, FUSEKI_PASSWORD)
            sw.setMethod(POST)
            sw.setQuery(full)
            sw.query()
            return
        with self._lock:
            self.graph.update(full)
            self._save_local()

    def reset(self) -> None:
        """Mode local uniquement : recharge l'ontologie d'origine (efface les ajouts)."""
        if self.mode == "local":
            with self._lock:
                self._load_local(reset=True)


client = SparqlClient()
