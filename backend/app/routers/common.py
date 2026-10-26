"""Routes communes : zones, statistiques, détail d'un individu, console SPARQL."""
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..queries import common as q
from ..sparql_client import client

router = APIRouter(prefix="/api", tags=["Commun"])


@router.get("/health")
def health():
    return {"status": "ok", "mode_sparql": client.mode}


@router.get("/zones")
def zones():
    return q.list_zones()


@router.get("/stats")
def stats():
    return q.stats()


@router.get("/individu/{nom}")
def individu(nom: str):
    rows = q.describe(nom)
    if not rows:
        raise HTTPException(404, f"Individu introuvable : {nom}")
    return rows


class RequeteSparql(BaseModel):
    requete: str


@router.post("/sparql")
def console(req: RequeteSparql):
    """Console SPARQL (lecture seule) pour la démo : SELECT / ASK uniquement."""
    if re.search(r"\b(INSERT|DELETE|LOAD|CLEAR|DROP|CREATE)\b", req.requete, re.I):
        raise HTTPException(400, "La console n'accepte que des requêtes de lecture (SELECT).")
    try:
        return client.select(req.requete)
    except Exception as e:  # erreur de syntaxe SPARQL
        raise HTTPException(400, f"Requête invalide : {e}")


@router.post("/reset")
def reset():
    """Mode local : remet les données d'origine (pratique avant la démo)."""
    client.reset()
    return {"message": "Données réinitialisées" if client.mode == "local"
            else "En mode Fuseki, relancez scripts/load_fuseki.py"}
