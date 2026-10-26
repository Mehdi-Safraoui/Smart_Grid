"""Routes API de la branche STOCKAGE (Mohamed Elyess).

👉 Modèle à suivre : routers/production.py
   La route GET (liste) est fournie. À faire : GET /{nom}, POST, PUT /{nom}, DELETE /{nom},
   avec des modèles Pydantic adaptés à votre branche.
"""
from fastapi import APIRouter

from ..queries import stockage as q

router = APIRouter(prefix="/api/stockage", tags=["Stockage"])


@router.get("")
def lister(type: str | None = None, zone: str | None = None, recherche: str | None = None):
    return q.lister(type, zone, recherche)


@router.get("/types")
def types():
    return q.TYPES


# TODO : @router.get("/{nom}")      -> q.obtenir(nom)
# TODO : @router.post("")            -> q.creer(...)
# TODO : @router.put("/{nom}")      -> q.modifier(nom, ...)
# TODO : @router.delete("/{nom}")   -> q.supprimer(nom)
