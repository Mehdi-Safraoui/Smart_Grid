"""
Branche CONSOMMATION (Ahmed Amine).

Classe racine : BatimentConsommateur   Types instanciables : BatimentResidentiel, BatimentCommercial, BatimentIndustriel
Attribut : consommationKWh
Relations : estSitueDans (Zone), estAlimentePar (Source ou Stockage)
Classes définies : GrosConsommateur, BatimentAlimenteRenouvelable

👉 Modèle à suivre : queries/production.py (même structure, mêmes noms de fonctions).
   La fonction lister() ci-dessous est fournie comme point de départ ; à vous de
   l'enrichir (filtres, recherche, relations) puis d'écrire creer / modifier / supprimer.
"""
from fastapi import HTTPException

from ..sparql_client import client
from .common import decimal, exists, safe_id, search_filter

TYPES = ['BatimentResidentiel', 'BatimentCommercial', 'BatimentIndustriel']


# ------------------------------------------------------------------ READ
def lister(type_: str | None = None, zone: str | None = None,
           recherche: str | None = None) -> list[dict]:
    filtres = []
    if type_:
        filtres.append(f"?batiment a/rdfs:subClassOf* sg:{safe_id(type_)} .")
    if zone:
        filtres.append(f"?batiment sg:estSitueDans sg:{safe_id(zone)} .")
    filtres.append(search_filter("?batiment", recherche))
    # TODO : filtres numériques sur consommationKWh (min / max), comme dans production.py
    q = f"""
    SELECT DISTINCT ?batiment ?type ?consommation ?zone WHERE {{
        ?batiment a ?type .
        ?type rdfs:subClassOf* sg:BatimentConsommateur .
        FILTER(?type IN (sg:BatimentResidentiel, sg:BatimentCommercial, sg:BatimentIndustriel))
        OPTIONAL {{ ?batiment sg:consommationKWh ?consommation }}
        OPTIONAL {{ ?batiment sg:estSitueDans ?zone }}
        {' '.join(filtres)}
    }} ORDER BY ?batiment"""
    return client.select(q)


# ------------------------------------------------------------------ CREATE
def creer(**donnees) -> None:
    # TODO : INSERT DATA (voir production.creer)
    raise HTTPException(501, "creer() pas encore implémenté pour la branche consommation")


# ------------------------------------------------------------------ UPDATE
def modifier(nom: str, **donnees) -> None:
    # TODO : DELETE / INSERT WHERE (voir production.modifier)
    raise HTTPException(501, "modifier() pas encore implémenté pour la branche consommation")


# ------------------------------------------------------------------ DELETE
def supprimer(nom: str) -> None:
    # TODO : DELETE WHERE (voir production.supprimer)
    raise HTTPException(501, "supprimer() pas encore implémenté pour la branche consommation")
