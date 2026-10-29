"""
Branche STOCKAGE (Mohamed Elyess).

Classes : SystemeStockage > Batterie
                          > StockageHydrogene
Attribut : capaciteStockageMWh
Relations : estSitueDans (Zone), stockeEnergieDe (SourceProduction), alimente (Bâtiment)

Les 4 opérations CRUD + filtrage + recherche (même structure que production.py) :
  READ   -> lister()        SELECT avec OPTIONAL, FILTER, CONTAINS, GROUP_CONCAT
  READ   -> obtenir()       SELECT sur un individu
  CREATE -> creer()         INSERT DATA
  UPDATE -> modifier()      DELETE / INSERT WHERE
  DELETE -> supprimer()     DELETE WHERE
"""
from fastapi import HTTPException

from ..sparql_client import client
from .common import decimal, exists, safe_id, search_filter

TYPES = ["Batterie", "StockageHydrogene"]   # classes instanciables


# ------------------------------------------------------------------ READ
def lister(type_: str | None = None, zone: str | None = None,
           min_mwh: float | None = None, max_mwh: float | None = None,
           source: str | None = None, recherche: str | None = None) -> list[dict]:
    filtres = []
    if type_:
        if type_ not in TYPES:
            raise HTTPException(400, f"Type inconnu : {type_}")
        filtres.append(f"?stockage a sg:{type_} .")
    if zone:
        filtres.append(f"?stockage sg:estSitueDans sg:{safe_id(zone)} .")
    if source:   # stockages qui stockent l'énergie d'une source donnée
        filtres.append(f"?stockage sg:stockeEnergieDe sg:{safe_id(source)} .")
    if min_mwh is not None:
        filtres.append(f"FILTER(?capacite >= {float(min_mwh)})")
    if max_mwh is not None:
        filtres.append(f"FILTER(?capacite <= {float(max_mwh)})")
    filtres.append(search_filter("?stockage", recherche))

    q = f"""
    SELECT ?stockage ?type ?capacite ?zone
           (GROUP_CONCAT(DISTINCT STRAFTER(STR(?src), "#"); separator=", ") AS ?stocke)
           (GROUP_CONCAT(DISTINCT STRAFTER(STR(?bat), "#"); separator=", ") AS ?alimente)
    WHERE {{
        ?stockage a ?type .
        FILTER(?type IN (sg:Batterie, sg:StockageHydrogene))
        OPTIONAL {{ ?stockage sg:capaciteStockageMWh ?capacite }}
        OPTIONAL {{ ?stockage sg:estSitueDans ?zone }}
        OPTIONAL {{ ?stockage sg:stockeEnergieDe ?src }}
        OPTIONAL {{ ?stockage sg:alimente ?bat }}
        {' '.join(filtres)}
    }}
    GROUP BY ?stockage ?type ?capacite ?zone
    ORDER BY DESC(?capacite)"""
    return client.select(q)


def obtenir(nom: str) -> dict:
    nom = safe_id(nom)
    rows = [r for r in lister() if r["stockage"] == nom]
    if not rows:
        raise HTTPException(404, f"Stockage introuvable : {nom}")
    return rows[0]


def capacite_par_type() -> list[dict]:
    """Agrégation : nombre de systèmes, capacité totale et moyenne par technologie."""
    q = """
    SELECT ?type (COUNT(?s) AS ?nombre) (SUM(?c) AS ?totalMWh) (AVG(?c) AS ?moyenneMWh)
    WHERE {
        ?s a ?type ; sg:capaciteStockageMWh ?c .
        FILTER(?type IN (sg:Batterie, sg:StockageHydrogene))
    } GROUP BY ?type ORDER BY DESC(?totalMWh)"""
    return client.select(q)


# ------------------------------------------------------------------ CREATE
def creer(nom: str, type_: str, capacite: float, zone: str,
          stocke: list[str], alimente: list[str] | None = None) -> None:
    nom, zone = safe_id(nom), safe_id(zone)
    if type_ not in TYPES:
        raise HTTPException(400, f"Type invalide : {type_} (attendu : {TYPES})")
    if not stocke:
        # restriction OWL : SystemeStockage ⊑ stockeEnergieDe some SourceProduction
        raise HTTPException(400, "Un système de stockage doit stocker l'énergie d'au moins une source")
    if exists(nom):
        raise HTTPException(409, f"'{nom}' existe déjà")
    lignes = [f"sg:{nom} a owl:NamedIndividual , sg:{type_} ;",
              f"    sg:capaciteStockageMWh {decimal(capacite)} ;",
              f"    sg:estSitueDans sg:{zone} ."]
    for s in stocke:
        lignes.append(f"sg:{nom} sg:stockeEnergieDe sg:{safe_id(s)} .")
    for b in alimente or []:
        b = safe_id(b)
        # on écrit les deux sens car le serveur SPARQL ne raisonne pas sur owl:inverseOf
        lignes.append(f"sg:{nom} sg:alimente sg:{b} . sg:{b} sg:estAlimentePar sg:{nom} .")
    client.update("INSERT DATA {\n" + "\n".join(lignes) + "\n}")


# ------------------------------------------------------------------ UPDATE
def modifier(nom: str, capacite: float | None = None, zone: str | None = None,
             stocke: list[str] | None = None) -> None:
    nom = safe_id(nom)
    if not exists(nom):
        raise HTTPException(404, f"Stockage introuvable : {nom}")
    if capacite is not None:
        client.update(f"""
        DELETE {{ sg:{nom} sg:capaciteStockageMWh ?ancienne }}
        INSERT {{ sg:{nom} sg:capaciteStockageMWh {decimal(capacite)} }}
        WHERE  {{ OPTIONAL {{ sg:{nom} sg:capaciteStockageMWh ?ancienne }} }}""")
    if zone is not None:
        zone = safe_id(zone)
        client.update(f"""
        DELETE {{ sg:{nom} sg:estSitueDans ?ancienne }}
        INSERT {{ sg:{nom} sg:estSitueDans sg:{zone} }}
        WHERE  {{ OPTIONAL {{ sg:{nom} sg:estSitueDans ?ancienne }} }}""")
    if stocke:   # remplace la ou les sources stockées
        sources = " ".join(f"sg:{nom} sg:stockeEnergieDe sg:{safe_id(s)} ." for s in stocke)
        client.update(f"""
        DELETE {{ sg:{nom} sg:stockeEnergieDe ?ancienne }}
        INSERT {{ {sources} }}
        WHERE  {{ OPTIONAL {{ sg:{nom} sg:stockeEnergieDe ?ancienne }} }}""")


# ------------------------------------------------------------------ DELETE
def supprimer(nom: str) -> None:
    nom = safe_id(nom)
    if not exists(nom):
        raise HTTPException(404, f"Stockage introuvable : {nom}")
    # supprime les triplets où l'individu est sujet, puis ceux où il est objet
    # (ex. « Usine_Sfax estAlimentePar nom »)
    client.update(f"DELETE WHERE {{ sg:{nom} ?p ?o }}")
    client.update(f"DELETE WHERE {{ ?s ?p sg:{nom} }}")
