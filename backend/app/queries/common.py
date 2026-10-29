"""Requêtes SPARQL partagées par toutes les branches (zones, statistiques, détail)."""
import re

from fastapi import HTTPException

from ..sparql_client import client

ID_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,80}$")


def safe_id(name: str) -> str:
    """Vérifie un identifiant d'individu avant de l'insérer dans une requête.
    Empêche l'injection SPARQL : seulement lettres, chiffres et '_'."""
    if not ID_PATTERN.match(name or ""):
        raise HTTPException(400, f"Identifiant invalide : '{name}' (lettres, chiffres et _ uniquement)")
    return name


def decimal(value: float) -> str:
    """Formate un nombre comme littéral xsd:decimal."""
    return f'"{float(value)}"^^xsd:decimal'


def search_filter(var: str, text: str | None) -> str:
    """Filtre de recherche (insensible à la casse) sur le nom de l'individu."""
    if not text:
        return ""
    cleaned = re.sub(r"[^\w-]", "_", text.strip()).lower()   # espaces -> _ comme dans les noms
    return f'FILTER(CONTAINS(LCASE(STR({var})), "{cleaned}"))'


def exists(individual: str) -> bool:
    rows = client.select(f"SELECT (COUNT(*) AS ?n) WHERE {{ sg:{individual} ?p ?o }}")
    return bool(rows) and int(rows[0].get("n", 0)) > 0


def changer_type(nom: str, type_: str, autorises: list[str]) -> None:
    """Change la classe d'un individu (DELETE / INSERT WHERE).
    On ne retire que les classes « instanciables » de la branche : owl:NamedIndividual et les
    classes déduites (GrosConsommateur…) restent intactes."""
    if type_ not in autorises:
        raise HTTPException(400, f"Type invalide : {type_} (attendu : {autorises})")
    anciens = ", ".join(f"sg:{t}" for t in autorises)
    client.update(f"""
    DELETE {{ sg:{nom} a ?ancien }}
    INSERT {{ sg:{nom} a sg:{type_} }}
    WHERE  {{ sg:{nom} a ?ancien . FILTER(?ancien IN ({anciens})) }}""")


def renommer(ancien: str, nouveau: str) -> str:
    """Renomme un individu : l'identifiant est son IRI, donc on réécrit tous ses triplets,
    d'abord comme sujet puis comme objet (une seule opération par appel)."""
    nouveau = safe_id(nouveau)
    if nouveau == ancien:
        return ancien
    if exists(nouveau):
        raise HTTPException(409, f"'{nouveau}' existe déjà")
    client.update(f"""
    DELETE {{ sg:{ancien} ?p ?o }} INSERT {{ sg:{nouveau} ?p ?o }}
    WHERE  {{ sg:{ancien} ?p ?o }}""")
    client.update(f"""
    DELETE {{ ?s ?p sg:{ancien} }} INSERT {{ ?s ?p sg:{nouveau} }}
    WHERE  {{ ?s ?p sg:{ancien} }}""")
    return nouveau


# ---------------------------------------------------------------- zones
def list_zones() -> list[str]:
    q = "SELECT ?zone WHERE { ?zone a sg:Zone } ORDER BY ?zone"
    return [r["zone"] for r in client.select(q)]


# ---------------------------------------------------------------- statistiques
BRANCHES = {
    "production": "SourceProduction",
    "stockage": "SystemeStockage",
    "consommation": "BatimentConsommateur",
    "reseau": "InfrastructureReseau",
}


def stats() -> dict:
    out = {}
    for branche, classe in BRANCHES.items():
        q = f"""SELECT (COUNT(DISTINCT ?x) AS ?n)
                WHERE {{ ?x a/rdfs:subClassOf* sg:{classe} }}"""
        out[branche] = int(client.select(q)[0]["n"])
    q = """SELECT ?type (SUM(?p) AS ?total) WHERE {
             ?s a/rdfs:subClassOf* ?type ; sg:puissanceMW ?p .
             VALUES ?type { sg:SourceRenouvelable sg:SourceFossile } } GROUP BY ?type"""
    out["puissance_mw"] = {r["type"]: r["total"] for r in client.select(q)}
    return out


# ---------------------------------------------------------------- détail
def describe(individual: str) -> list[dict]:
    """Toutes les propriétés d'un individu (dans les deux sens)."""
    individual = safe_id(individual)
    q = f"""SELECT ?propriete ?valeur ?sens WHERE {{
              {{ sg:{individual} ?propriete ?valeur . BIND("sortant" AS ?sens) }}
              UNION
              {{ ?valeur ?propriete sg:{individual} . BIND("entrant" AS ?sens) }}
              FILTER(?propriete != rdf:type || ?valeur != owl:NamedIndividual)
            }}"""
    return client.select(q)
