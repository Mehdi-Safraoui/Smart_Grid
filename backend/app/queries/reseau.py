"""
Branche RESEAU (Yassine).

Classes : InfrastructureReseau > LigneElectrique > LigneTransport / LigneDistribution
                               > PosteTransformation
Attribut : tensionKV (lignes seulement)
Relations : estSitueDans (Zone), relie (une ligne relie au moins 2 composants)

Même structure que queries/production.py :
  READ   -> lister()        SELECT avec OPTIONAL, GROUP_CONCAT, FILTER, CONTAINS
  READ   -> obtenir()       SELECT sur un individu
  CREATE -> creer()         INSERT DATA
  UPDATE -> modifier()      DELETE / INSERT WHERE
  DELETE -> supprimer()     DELETE WHERE
  BONUS  -> parcours()      chemin de l'énergie en suivant la relation relie
"""
from collections import deque

from fastapi import HTTPException

from ..sparql_client import client
from .common import changer_type, decimal, exists, renommer, safe_id, search_filter

TYPES = ['LigneTransport', 'LigneDistribution', 'PosteTransformation']   # classes instanciables
LIGNES = ['LigneTransport', 'LigneDistribution']


# ------------------------------------------------------------------ READ
def lister(type_: str | None = None, zone: str | None = None,
           min_kv: float | None = None, max_kv: float | None = None,
           recherche: str | None = None, relie_a: str | None = None) -> list[dict]:
    filtres = []
    if type_:
        if type_ not in TYPES + ["LigneElectrique"]:
            raise HTTPException(400, f"Type inconnu : {type_}")
        filtres.append(f"?element a/rdfs:subClassOf* sg:{type_} .")
    if zone:
        filtres.append(f"?element sg:estSitueDans sg:{safe_id(zone)} .")
    if min_kv is not None:
        filtres.append(f"FILTER(?tension >= {float(min_kv)})")
    if max_kv is not None:
        filtres.append(f"FILTER(?tension <= {float(max_kv)})")
    if relie_a:
        # les lignes qui relient ce composant
        filtres.append(f"?element sg:relie sg:{safe_id(relie_a)} .")
    filtres.append(search_filter("?element", recherche))

    q = f"""
    SELECT ?element ?type ?tension ?zone
           (GROUP_CONCAT(DISTINCT COALESCE(STRAFTER(STR(?x), "#"), ""); separator=", ") AS ?relie)
    WHERE {{
        ?element a ?type .
        FILTER(?type IN (sg:LigneTransport, sg:LigneDistribution, sg:PosteTransformation))
        OPTIONAL {{ ?element sg:tensionKV ?tension }}
        OPTIONAL {{ ?element sg:estSitueDans ?zone }}
        OPTIONAL {{ ?element sg:relie ?x }}      # un poste n'a pas de relie -> COALESCE ""
        {' '.join(filtres)}
    }}
    GROUP BY ?element ?type ?tension ?zone
    ORDER BY DESC(?tension) ?element"""
    return client.select(q)


def obtenir(element_id: str) -> dict:
    element_id = safe_id(element_id)
    rows = [r for r in lister() if r["element"] == element_id]
    if not rows:
        raise HTTPException(404, f"Élément du réseau introuvable : {element_id}")
    return rows[0]


def _verifier_relie(relie: list[str]) -> list[str]:
    """Une ligne relie au moins 2 composants distincts du smart grid (restriction min 2)."""
    relie = list(dict.fromkeys(safe_id(x) for x in relie))   # sans doublons, ordre conservé
    if len(relie) < 2:
        raise HTTPException(400, "Une ligne doit relier au moins 2 éléments (restriction relie min 2)")
    valeurs = " ".join(f"sg:{x}" for x in relie)
    q = f"""SELECT DISTINCT ?x WHERE {{
              VALUES ?x {{ {valeurs} }}
              ?x a/rdfs:subClassOf* sg:ComposantSmartGrid }}"""
    trouves = {r["x"] for r in client.select(q)}
    inconnus = [x for x in relie if x not in trouves]
    if inconnus:
        raise HTTPException(400, f"Composant(s) introuvable(s) : {', '.join(inconnus)}")
    return relie


# ------------------------------------------------------------------ CREATE
def creer(nom: str, type_: str, zone: str, tension: float | None = None,
          relie: list[str] | None = None) -> None:
    nom, zone = safe_id(nom), safe_id(zone)
    if type_ not in TYPES:
        raise HTTPException(400, f"Type invalide : {type_} (attendu : {TYPES})")
    if exists(nom):
        raise HTTPException(409, f"'{nom}' existe déjà")
    lignes = [f"sg:{nom} a owl:NamedIndividual , sg:{type_} ;",
              f"    sg:estSitueDans sg:{zone} ."]
    if type_ in LIGNES:
        if tension is None:
            raise HTTPException(400, "La tension (kV) est obligatoire pour une ligne")
        lignes.append(f"sg:{nom} sg:tensionKV {decimal(tension)} .")
        for x in _verifier_relie(relie or []):
            lignes.append(f"sg:{nom} sg:relie sg:{x} .")
    elif tension is not None or relie:
        # domaine de tensionKV et de relie = LigneElectrique, disjointe de PosteTransformation :
        # HermiT déclarerait l'ontologie incohérente
        raise HTTPException(400, "Un poste de transformation n'a ni tension ni relation relie")
    client.update("INSERT DATA {\n" + "\n".join(lignes) + "\n}")


# ------------------------------------------------------------------ UPDATE
def modifier(nom: str, tension: float | None = None, zone: str | None = None,
             relie: list[str] | None = None, type_: str | None = None,
             nouveau_nom: str | None = None) -> str:
    nom = safe_id(nom)
    element = obtenir(nom)
    if nouveau_nom:
        safe_id(nouveau_nom)
    if type_ and type_ != element["type"]:
        # transport <-> distribution seulement : un poste n'a ni tension ni relie
        if element["type"] not in LIGNES or type_ not in LIGNES:
            raise HTTPException(400, "Le type ne peut changer qu'entre ligne de transport et de distribution")
        changer_type(nom, type_, LIGNES)
    if (tension is not None or relie is not None) and element["type"] not in LIGNES:
        raise HTTPException(400, "Un poste de transformation n'a ni tension ni relation relie")
    if relie is not None:
        relie = _verifier_relie(relie)       # on valide avant toute modification
    if tension is not None:
        client.update(f"""
        DELETE {{ sg:{nom} sg:tensionKV ?ancienne }}
        INSERT {{ sg:{nom} sg:tensionKV {decimal(tension)} }}
        WHERE  {{ OPTIONAL {{ sg:{nom} sg:tensionKV ?ancienne }} }}""")
    if zone is not None:
        zone = safe_id(zone)
        client.update(f"""
        DELETE {{ sg:{nom} sg:estSitueDans ?ancienne }}
        INSERT {{ sg:{nom} sg:estSitueDans sg:{zone} }}
        WHERE  {{ OPTIONAL {{ sg:{nom} sg:estSitueDans ?ancienne }} }}""")
    if relie is not None:
        nouveaux = " ".join(f"sg:{nom} sg:relie sg:{x} ." for x in relie)
        client.update(f"""
        DELETE {{ sg:{nom} sg:relie ?ancien }}
        INSERT {{ {nouveaux} }}
        WHERE  {{ OPTIONAL {{ sg:{nom} sg:relie ?ancien }} }}""")
    return renommer(nom, nouveau_nom) if nouveau_nom else nom   # en dernier


# ------------------------------------------------------------------ DELETE
def supprimer(nom: str) -> list[str]:
    """Supprime l'élément et renvoie les lignes qui relient désormais moins de 2 éléments."""
    nom = safe_id(nom)
    if not exists(nom):
        raise HTTPException(404, f"Élément du réseau introuvable : {nom}")
    # supprime les triplets où l'individu est sujet, puis ceux où il est objet
    client.update(f"DELETE WHERE {{ sg:{nom} ?p ?o }}")
    client.update(f"DELETE WHERE {{ ?s ?p sg:{nom} }}")
    q = """SELECT ?ligne WHERE {
             ?ligne a/rdfs:subClassOf* sg:LigneElectrique .
             OPTIONAL { ?ligne sg:relie ?x }
           } GROUP BY ?ligne HAVING (COUNT(DISTINCT ?x) < 2)"""
    return [r["ligne"] for r in client.select(q)]


# ------------------------------------------------------------------ BONUS : parcours
def parcours(depart: str, arrivee: str) -> list[dict]:
    """Chemin de l'énergie entre deux composants, en passant par les lignes (relie).
    Exemple : Centrale_Solaire_Tozeur -> Ligne_Tozeur_Sfax -> Poste_Sfax -> ... -> Usine_Sfax"""
    depart, arrivee = safe_id(depart), safe_id(arrivee)
    for x in (depart, arrivee):
        if not exists(x):
            raise HTTPException(404, f"Composant introuvable : {x}")
    # graphe non orienté : chaque ligne est voisine des composants qu'elle relie
    voisins: dict[str, set[str]] = {}
    for r in client.select("SELECT ?ligne ?x WHERE { ?ligne sg:relie ?x }"):
        voisins.setdefault(r["ligne"], set()).add(r["x"])
        voisins.setdefault(r["x"], set()).add(r["ligne"])

    # parcours en largeur : donne le chemin le plus court
    precedent = {depart: None}
    file = deque([depart])
    while file and arrivee not in precedent:
        noeud = file.popleft()
        for v in sorted(voisins.get(noeud, ())):
            if v not in precedent:
                precedent[v] = noeud
                file.append(v)
    if arrivee not in precedent:
        raise HTTPException(404, f"Aucun chemin entre {depart} et {arrivee}")
    chemin = [arrivee]
    while chemin[-1] != depart:
        chemin.append(precedent[chemin[-1]])
    chemin.reverse()

    # type le plus précis de chaque étape (celui qui n'a pas de sous-classe parmi ses types)
    valeurs = " ".join(f"sg:{x}" for x in chemin)
    q = f"""SELECT ?x ?type ?tension WHERE {{
              VALUES ?x {{ {valeurs} }}
              ?x a ?type . ?type rdfs:subClassOf* sg:ComposantSmartGrid .
              FILTER NOT EXISTS {{ ?x a ?sous . ?sous rdfs:subClassOf ?type . FILTER(?sous != ?type) }}
              OPTIONAL {{ ?x sg:tensionKV ?tension }}
            }}"""
    infos = {r["x"]: r for r in client.select(q)}
    return [{"element": x, "type": infos.get(x, {}).get("type"),
             "tension": infos.get(x, {}).get("tension")} for x in chemin]
