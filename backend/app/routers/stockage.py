"""Routes API de la branche STOCKAGE (Mohamed Elyess)."""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from .. import raisonnement
from ..queries import stockage as q

router = APIRouter(prefix="/api/stockage", tags=["Stockage"])


class StockageIn(BaseModel):
    nom: str = Field(..., examples=["Batterie_Sfax"])
    type: str = Field(..., examples=["Batterie"])
    capacite: float = Field(..., gt=0, examples=[40.0])
    zone: str = Field(..., examples=["Zone_Sfax"])
    stocke: list[str] = Field(..., min_length=1, examples=[["Centrale_Solaire_Tozeur"]])
    alimente: list[str] = Field(default_factory=list, examples=[["Usine_Sfax"]])


class StockageUpdate(BaseModel):
    capacite: float | None = Field(None, gt=0)
    zone: str | None = None
    stocke: list[str] | None = None
    alimente: list[str] | None = None
    type: str | None = None
    nouveau_nom: str | None = None


@router.get("")
def lister(type: str | None = None, zone: str | None = None,
           min_mwh: float | None = None, max_mwh: float | None = None,
           source: str | None = None, recherche: str | None = None):
    """Liste les stockages, avec filtres optionnels
    (type, zone, capacité min/max, source stockée, recherche)."""
    return q.lister(type, zone, min_mwh, max_mwh, source, recherche)


@router.get("/types")
def types():
    return q.TYPES


@router.get("/statistiques")
def statistiques():
    """Nombre, capacité totale et moyenne par technologie (COUNT / SUM / AVG + GROUP BY)."""
    return q.capacite_par_type()


@router.post("/raisonner")
def raisonner(enregistrer: bool = False, tester_incoherence: bool = False):
    """Valeur ajoutée : lance HermiT sur les données actuelles et renvoie les déductions.
    - enregistrer=true : écrit les nouvelles déductions dans le serveur SPARQL
    - tester_incoherence=true : démonstration (Batterie_Tozeur déclarée aussi hydrogène)"""
    return raisonnement.raisonner(enregistrer, tester_incoherence)


@router.get("/{nom}")
def obtenir(nom: str):
    return q.obtenir(nom)


@router.post("", status_code=201)
def creer(s: StockageIn):
    q.creer(s.nom, s.type, s.capacite, s.zone, s.stocke, s.alimente)
    return {"message": f"{s.nom} ajouté"}


@router.put("/{nom}")
def modifier(nom: str, maj: StockageUpdate):
    nouveau = q.modifier(nom, maj.capacite, maj.zone, maj.stocke, maj.alimente, maj.type, maj.nouveau_nom)
    return {"message": f"{nouveau} modifié", "nom": nouveau}


@router.delete("/{nom}")
def supprimer(nom: str):
    q.supprimer(nom)
    return {"message": f"{nom} supprimé"}
