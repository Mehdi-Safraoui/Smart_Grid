"""Routes API de la branche RÉSEAU (Yassine)."""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..queries import reseau as q

router = APIRouter(prefix="/api/reseau", tags=["Réseau"])


class ElementIn(BaseModel):
    nom: str = Field(..., examples=["Ligne_Kairouan_Sfax"])
    type: str = Field(..., examples=["LigneTransport"])
    zone: str = Field(..., examples=["Zone_Kairouan"])
    tension: float | None = Field(None, gt=0, examples=[225.0])      # lignes seulement
    relie: list[str] = Field(default_factory=list, examples=[["Poste_Kairouan", "Poste_Sfax"]])


class ElementUpdate(BaseModel):
    tension: float | None = Field(None, gt=0)
    zone: str | None = None
    relie: list[str] | None = None
    type: str | None = None
    nouveau_nom: str | None = None


@router.get("")
def lister(type: str | None = None, zone: str | None = None,
           min_kv: float | None = None, max_kv: float | None = None,
           recherche: str | None = None, relie_a: str | None = None):
    """Liste les lignes et postes, avec filtres optionnels (type, zone, tension min/max,
    recherche, lignes qui relient un composant)."""
    return q.lister(type, zone, min_kv, max_kv, recherche, relie_a)


@router.get("/types")
def types():
    return q.TYPES


@router.get("/parcours")
def parcours(depart: str, arrivee: str):
    """Chemin de l'énergie entre deux composants en suivant les lignes (relie)."""
    return q.parcours(depart, arrivee)


@router.get("/{nom}")
def obtenir(nom: str):
    return q.obtenir(nom)


@router.post("", status_code=201)
def creer(element: ElementIn):
    q.creer(element.nom, element.type, element.zone, element.tension, element.relie)
    return {"message": f"{element.nom} ajouté"}


@router.put("/{nom}")
def modifier(nom: str, maj: ElementUpdate):
    nouveau = q.modifier(nom, maj.tension, maj.zone, maj.relie, maj.type, maj.nouveau_nom)
    return {"message": f"{nouveau} modifié", "nom": nouveau}


@router.delete("/{nom}")
def supprimer(nom: str):
    lignes = q.supprimer(nom)
    return {"message": f"{nom} supprimé", "lignes_incompletes": lignes}
