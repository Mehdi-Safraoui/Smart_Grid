"""Routes API de la branche CONSOMMATION (Ahmed Amine)."""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..queries import consommation as q

router = APIRouter(prefix="/api/consommation", tags=["Consommation"])


class BatimentIn(BaseModel):
    nom: str = Field(..., examples=["Hopital_Sfax"])
    type: str = Field(..., examples=["BatimentCommercial"])
    consommation: float = Field(..., gt=0, examples=[300000.0])
    zone: str = Field(..., examples=["Zone_Sfax"])
    alimente_par: list[str] = Field(default_factory=list, examples=[["Centrale_Solaire_Tozeur"]])


class BatimentUpdate(BaseModel):
    consommation: float | None = Field(None, gt=0)
    zone: str | None = None
    alimente_par: list[str] | None = None


@router.get("")
def lister(type: str | None = None, zone: str | None = None,
           min_kwh: float | None = None, max_kwh: float | None = None,
           recherche: str | None = None, alimente_par: str | None = None,
           gros: bool | None = None, renouvelable: bool | None = None):
    """Liste les bâtiments, avec filtres optionnels (type, zone, consommation min/max, recherche,
    fournisseur, gros consommateur, alimenté en renouvelable)."""
    return q.lister(type, zone, min_kwh, max_kwh, recherche, alimente_par, gros, renouvelable)


@router.get("/types")
def types():
    return q.TYPES


@router.get("/gros-consommateurs")
def gros_consommateurs(seuil: float = q.SEUIL_GROS):
    """Classe définie GrosConsommateur, recalculée en SPARQL (seuil réglable)."""
    return q.gros_consommateurs(seuil)


@router.get("/renouvelables")
def renouvelables():
    """Classe définie BatimentAlimenteRenouvelable, recalculée en SPARQL."""
    return q.alimentes_renouvelable()


@router.get("/par-zone")
def par_zone():
    return q.par_zone()


@router.get("/carte")
def carte():
    return q.carte()


@router.get("/fournisseurs")
def fournisseurs():
    return q.fournisseurs()


@router.post("/classer")
def classer():
    """Recalcule les types GrosConsommateur / BatimentAlimenteRenouvelable (règles SPARQL)."""
    return q.classer()


@router.get("/{nom}")
def obtenir(nom: str):
    return q.obtenir(nom)


@router.post("", status_code=201)
def creer(b: BatimentIn):
    q.creer(b.nom, b.type, b.consommation, b.zone, b.alimente_par)
    return {"message": f"{b.nom} ajouté"}


@router.put("/{nom}")
def modifier(nom: str, maj: BatimentUpdate):
    q.modifier(nom, maj.consommation, maj.zone, maj.alimente_par)
    return {"message": f"{nom} modifié"}


@router.delete("/{nom}")
def supprimer(nom: str):
    q.supprimer(nom)
    return {"message": f"{nom} supprimé"}
