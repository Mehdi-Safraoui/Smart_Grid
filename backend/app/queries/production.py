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
from .common import changer_type, decimal, exists, renommer, safe_id, search_filter

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


# ------------------------------------------------------------------ TABLEAU DE BORD
# Requêtes d'agrégation (SUM, COUNT, GROUP BY) : valeur ajoutée de la branche Production.
def tableau_de_bord() -> dict:
    # 1) Puissance totale par catégorie (renouvelable / fossile)
    par_categorie = client.select("""
    SELECT ?categorie (SUM(?p) AS ?puissance) (COUNT(DISTINCT ?s) AS ?nombre) WHERE {
        VALUES ?categorie { sg:SourceRenouvelable sg:SourceFossile }
        ?s a/rdfs:subClassOf* ?categorie ;
           sg:puissanceMW ?p .
    } GROUP BY ?categorie""")

    # 2) Puissance par zone, séparée renouvelable / fossile
    par_zone = client.select("""
    SELECT ?zone ?categorie (SUM(?p) AS ?puissance) WHERE {
        VALUES ?categorie { sg:SourceRenouvelable sg:SourceFossile }
        ?s a/rdfs:subClassOf* ?categorie ;
           sg:puissanceMW ?p ;
           sg:estSitueDans ?zone .
    } GROUP BY ?zone ?categorie""")

    # 3) Puissance par type de source (classe la plus précise)
    par_type = client.select("""
    SELECT ?type (SUM(?p) AS ?puissance) (COUNT(DISTINCT ?s) AS ?nombre) WHERE {
        VALUES ?type { sg:CentraleSolaire sg:ParcEolien sg:SourceFossile }
        ?s a ?type ;
           sg:puissanceMW ?p .
    } GROUP BY ?type ORDER BY DESC(?puissance)""")

    # 4) Puissance renouvelable reçue par chaque bâtiment (via la relation alimente)
    par_batiment = client.select("""
    SELECT ?batiment (SUM(?p) AS ?puissance) (COUNT(DISTINCT ?s) AS ?sources) WHERE {
        ?s a/rdfs:subClassOf* sg:SourceRenouvelable ;
           sg:puissanceMW ?p ;
           sg:alimente ?batiment .
    } GROUP BY ?batiment ORDER BY DESC(?puissance)""")

    totaux = {r["categorie"]: r for r in par_categorie}
    ren = totaux.get("SourceRenouvelable", {}).get("puissance", 0.0)
    fos = totaux.get("SourceFossile", {}).get("puissance", 0.0)
    zones: dict[str, dict] = {}
    for r in par_zone:
        z = zones.setdefault(r["zone"], {"zone": r["zone"], "renouvelable": 0.0, "fossile": 0.0})
        z["renouvelable" if r["categorie"] == "SourceRenouvelable" else "fossile"] = r["puissance"]
    return {
        "total_mw": ren + fos,
        "renouvelable_mw": ren,
        "fossile_mw": fos,
        "part_renouvelable": round(100 * ren / (ren + fos), 1) if ren + fos else 0.0,
        "nombre_sources": sum(int(r["nombre"]) for r in par_categorie),
        "par_zone": sorted(zones.values(), key=lambda z: -(z["renouvelable"] + z["fossile"])),
        "par_type": par_type,
        "par_batiment": par_batiment,
    }


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
def modifier(nom: str, puissance: float | None = None, zone: str | None = None,
             type_: str | None = None, nouveau_nom: str | None = None) -> str:
    nom = safe_id(nom)
    if not exists(nom):
        raise HTTPException(404, f"Source introuvable : {nom}")
    if nouveau_nom:
        safe_id(nouveau_nom)
    if type_:
        changer_type(nom, type_, TYPES)
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
    return renommer(nom, nouveau_nom) if nouveau_nom else nom   # en dernier : les autres MAJ utilisent l'ancien nom


# ------------------------------------------------------------------ DELETE
def supprimer(nom: str) -> None:
    nom = safe_id(nom)
    if not exists(nom):
        raise HTTPException(404, f"Source introuvable : {nom}")
    # supprime les triplets où l'individu est sujet, puis ceux où il est objet
    client.update(f"DELETE WHERE {{ sg:{nom} ?p ?o }}")
    client.update(f"DELETE WHERE {{ ?s ?p sg:{nom} }}")
