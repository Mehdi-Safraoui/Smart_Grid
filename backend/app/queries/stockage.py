"""
Branche STOCKAGE (Mohamed Elyess).

Classe racine : SystemeStockage   Types instanciables : Batterie, StockageHydrogene
Attribut : capaciteStockageMWh
Relations : estSitueDans (Zone), stockeEnergieDe (SourceProduction), alimente (Bâtiment)

👉 Modèle à suivre : queries/production.py (même structure, mêmes noms de fonctions).
   La fonction lister() ci-dessous est fournie comme point de départ ; à vous de
   l'enrichir (filtres, recherche, relations) puis d'écrire creer / modifier / supprimer.
"""
from fastapi import HTTPException

from ..sparql_client import client
from .common import decimal, exists, safe_id, search_filter

TYPES = ['Batterie', 'StockageHydrogene']


# ------------------------------------------------------------------ READ
def lister(type_: str | None = None, zone: str | None = None,
           recherche: str | None = None) -> list[dict]:
    filtres = []
    if type_:
        filtres.append(f"?stockage a/rdfs:subClassOf* sg:{safe_id(type_)} .")
    if zone:
        filtres.append(f"?stockage sg:estSitueDans sg:{safe_id(zone)} .")
    filtres.append(search_filter("?stockage", recherche))
    # TODO : filtres numériques sur capaciteStockageMWh (min / max), comme dans production.py
    q = f"""
    SELECT DISTINCT ?stockage ?type ?capacite ?zone WHERE {{
        ?stockage a ?type .
        ?type rdfs:subClassOf* sg:SystemeStockage .
        FILTER(?type IN (sg:Batterie, sg:StockageHydrogene))
        OPTIONAL {{ ?stockage sg:capaciteStockageMWh ?capacite }}
        OPTIONAL {{ ?stockage sg:estSitueDans ?zone }}
        {' '.join(filtres)}
    }} ORDER BY ?stockage"""
    return client.select(q)


# ------------------------------------------------------------------ CREATE
def creer(**donnees) -> None:
    # TODO : INSERT DATA (voir production.creer)
    raise HTTPException(501, "creer() pas encore implémenté pour la branche stockage")


# ------------------------------------------------------------------ UPDATE
def modifier(nom: str, **donnees) -> None:
    # TODO : DELETE / INSERT WHERE (voir production.modifier)
    raise HTTPException(501, "modifier() pas encore implémenté pour la branche stockage")


# ------------------------------------------------------------------ DELETE
def supprimer(nom: str) -> None:
    # TODO : DELETE WHERE (voir production.supprimer)
    raise HTTPException(501, "supprimer() pas encore implémenté pour la branche stockage")
