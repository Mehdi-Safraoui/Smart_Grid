"""
Branche PRODUCTION (Mehdi) — EXEMPLE COMPLET À SUIVRE PAR LES AUTRES BRANCHES.

Classes : SourceProduction > SourceRenouvelable > CentraleSolaire / ParcEolien
                           > SourceFossile
Attribut : puissanceMW      Relations : estSitueDans (Zone), alimente (Bâtiment)

On y trouve les 4 opérations CRUD + filtrage + recherche :
  READ   -> lister()        SELECT avec OPTIONAL, FILTER, CONTAINS
  READ   -> obtenir()       SELECT sur un individu
  CREATE -> creer()         INSERT DATA
  UPDATE -> modifier()      DELETE / INSERT WHERE
  DELETE -> supprimer()     DELETE WHERE
"""
from fastapi import HTTPException

from ..sparql_client import client
from .common import decimal, exists, safe_id, search_filter

TYPES = ["CentraleSolaire", "ParcEolien", "SourceFossile"]   # classes instanciables


# ------------------------------------------------------------------ READ
def lister(type_: str | None = None, zone: str | None = None,
           min_mw: float | None = None, max_mw: float | None = None,
           recherche: str | None = None) -> list[dict]:
    filtres = []
    if type_:
        if type_ not in TYPES + ["SourceRenouvelable"]:
            raise HTTPException(400, f"Type inconnu : {type_}")
        filtres.append(f"?source a/rdfs:subClassOf* sg:{type_} .")
    if zone:
        filtres.append(f"?source sg:estSitueDans sg:{safe_id(zone)} .")
    if min_mw is not None:
        filtres.append(f"FILTER(?puissance >= {float(min_mw)})")
    if max_mw is not None:
        filtres.append(f"FILTER(?puissance <= {float(max_mw)})")
    filtres.append(search_filter("?source", recherche))

    q = f"""
    SELECT ?source ?type ?puissance ?zone
           (GROUP_CONCAT(DISTINCT STRAFTER(STR(?bat), "#"); separator=", ") AS ?alimente)
    WHERE {{
        ?source a ?type .
        ?type rdfs:subClassOf* sg:SourceProduction .
        OPTIONAL {{ ?source sg:puissanceMW ?puissance }}
        OPTIONAL {{ ?source sg:estSitueDans ?zone }}
        OPTIONAL {{ ?source sg:alimente ?bat }}
        {' '.join(filtres)}
    }}
    GROUP BY ?source ?type ?puissance ?zone
    ORDER BY DESC(?puissance)"""
    return client.select(q)


def obtenir(source_id: str) -> dict:
    source_id = safe_id(source_id)
    rows = [r for r in lister() if r["source"] == source_id]
    if not rows:
        raise HTTPException(404, f"Source introuvable : {source_id}")
    return rows[0]


# ------------------------------------------------------------------ CREATE
def creer(nom: str, type_: str, puissance: float, zone: str,
          alimente: list[str] | None = None) -> None:
    nom, zone = safe_id(nom), safe_id(zone)
    if type_ not in TYPES:
        raise HTTPException(400, f"Type invalide : {type_} (attendu : {TYPES})")
    if exists(nom):
        raise HTTPException(409, f"'{nom}' existe déjà")
    lignes = [f"sg:{nom} a owl:NamedIndividual , sg:{type_} ;",
              f"    sg:puissanceMW {decimal(puissance)} ;",
              f"    sg:estSitueDans sg:{zone} ."]
    for b in alimente or []:
        b = safe_id(b)
        # on écrit les deux sens car le serveur SPARQL ne raisonne pas sur owl:inverseOf
        lignes.append(f"sg:{nom} sg:alimente sg:{b} . sg:{b} sg:estAlimentePar sg:{nom} .")
    client.update("INSERT DATA {\n" + "\n".join(lignes) + "\n}")


# ------------------------------------------------------------------ UPDATE
def modifier(nom: str, puissance: float | None = None, zone: str | None = None) -> None:
    nom = safe_id(nom)
    if not exists(nom):
        raise HTTPException(404, f"Source introuvable : {nom}")
    if puissance is not None:
        client.update(f"""
        DELETE {{ sg:{nom} sg:puissanceMW ?ancienne }}
        INSERT {{ sg:{nom} sg:puissanceMW {decimal(puissance)} }}
        WHERE  {{ OPTIONAL {{ sg:{nom} sg:puissanceMW ?ancienne }} }}""")
    if zone is not None:
        zone = safe_id(zone)
        client.update(f"""
        DELETE {{ sg:{nom} sg:estSitueDans ?ancienne }}
        INSERT {{ sg:{nom} sg:estSitueDans sg:{zone} }}
        WHERE  {{ OPTIONAL {{ sg:{nom} sg:estSitueDans ?ancienne }} }}""")


# ------------------------------------------------------------------ DELETE
def supprimer(nom: str) -> None:
    nom = safe_id(nom)
    if not exists(nom):
        raise HTTPException(404, f"Source introuvable : {nom}")
    # supprime les triplets où l'individu est sujet, puis ceux où il est objet
    client.update(f"DELETE WHERE {{ sg:{nom} ?p ?o }}")
    client.update(f"DELETE WHERE {{ ?s ?p sg:{nom} }}")
