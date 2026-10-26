"""
Branche RESEAU (Yassine).

Classe racine : InfrastructureReseau   Types instanciables : LigneTransport, LigneDistribution, PosteTransformation
Attribut : tensionKV
Relations : estSitueDans (Zone), relie (au moins 2 composants)

👉 Modèle à suivre : queries/production.py (même structure, mêmes noms de fonctions).
   La fonction lister() ci-dessous est fournie comme point de départ ; à vous de
   l'enrichir (filtres, recherche, relations) puis d'écrire creer / modifier / supprimer.
"""
from fastapi import HTTPException

from ..sparql_client import client
from .common import decimal, exists, safe_id, search_filter

TYPES = ['LigneTransport', 'LigneDistribution', 'PosteTransformation']


# ------------------------------------------------------------------ READ
def lister(type_: str | None = None, zone: str | None = None,
           recherche: str | None = None) -> list[dict]:
    filtres = []
    if type_:
        filtres.append(f"?element a/rdfs:subClassOf* sg:{safe_id(type_)} .")
    if zone:
        filtres.append(f"?element sg:estSitueDans sg:{safe_id(zone)} .")
    filtres.append(search_filter("?element", recherche))
    # TODO : filtres numériques sur tensionKV (min / max), comme dans production.py
    q = f"""
    SELECT DISTINCT ?element ?type ?tension ?zone WHERE {{
        ?element a ?type .
        ?type rdfs:subClassOf* sg:InfrastructureReseau .
        FILTER(?type IN (sg:LigneTransport, sg:LigneDistribution, sg:PosteTransformation))
        OPTIONAL {{ ?element sg:tensionKV ?tension }}
        OPTIONAL {{ ?element sg:estSitueDans ?zone }}
        {' '.join(filtres)}
    }} ORDER BY ?element"""
    return client.select(q)


# ------------------------------------------------------------------ CREATE
def creer(**donnees) -> None:
    # TODO : INSERT DATA (voir production.creer)
    raise HTTPException(501, "creer() pas encore implémenté pour la branche reseau")


# ------------------------------------------------------------------ UPDATE
def modifier(nom: str, **donnees) -> None:
    # TODO : DELETE / INSERT WHERE (voir production.modifier)
    raise HTTPException(501, "modifier() pas encore implémenté pour la branche reseau")


# ------------------------------------------------------------------ DELETE
def supprimer(nom: str) -> None:
    # TODO : DELETE WHERE (voir production.supprimer)
    raise HTTPException(501, "supprimer() pas encore implémenté pour la branche reseau")
