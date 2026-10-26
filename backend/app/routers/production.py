"""Routes API de la branche PRODUCTION (Mehdi) — exemple complet."""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..queries import production as q

router = APIRouter(prefix="/api/production", tags=["Production"])


class SourceIn(BaseModel):
    nom: str = Field(..., examples=["Centrale_Solaire_Gafsa"])
    type: str = Field(..., examples=["CentraleSolaire"])
    puissance: float = Field(..., gt=0, examples=[100.0])
    zone: str = Field(..., examples=["Zone_Tozeur"])
    alimente: list[str] = Field(default_factory=list, examples=[["Usine_Sfax"]])


class SourceUpdate(BaseModel):
    puissance: float | None = Field(None, gt=0)
    zone: str | None = None


@router.get("")
def lister(type: str | None = None, zone: str | None = None,
           min_mw: float | None = None, max_mw: float | None = None,
           recherche: str | None = None):
    """Liste les sources, avec filtres optionnels (type, zone, puissance min/max, recherche)."""
    return q.lister(type, zone, min_mw, max_mw, recherche)


@router.get("/types")
def types():
    return q.TYPES


@router.get("/tableau-de-bord")
def tableau_de_bord():
    """Indicateurs agrégés : puissance renouvelable / fossile, par zone, par type, par bâtiment."""
    return q.tableau_de_bord()


@router.get("/{nom}")
def obtenir(nom: str):
    return q.obtenir(nom)


@router.post("", status_code=201)
def creer(source: SourceIn):
    q.creer(source.nom, source.type, source.puissance, source.zone, source.alimente)
    return {"message": f"{source.nom} ajoutée"}


@router.put("/{nom}")
def modifier(nom: str, maj: SourceUpdate):
    q.modifier(nom, maj.puissance, maj.zone)
    return {"message": f"{nom} modifiée"}


@router.delete("/{nom}")
def supprimer(nom: str):
    q.supprimer(nom)
    return {"message": f"{nom} supprimée"}
