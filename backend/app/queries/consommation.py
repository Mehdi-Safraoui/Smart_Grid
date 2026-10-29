"""
Branche CONSOMMATION (Ahmed Amine).

Classes : BatimentConsommateur > BatimentResidentiel / BatimentCommercial / BatimentIndustriel
Attribut : consommationKWh      Relations : estSitueDans (Zone), estAlimentePar (Source ou Stockage)
Classes définies (EquivalentTo, remplies par HermiT) :
  GrosConsommateur              = BatimentConsommateur ⊓ consommationKWh some float[>= 100000]
  BatimentAlimenteRenouvelable  = BatimentConsommateur ⊓ estAlimentePar some SourceRenouvelable

On y trouve les 4 opérations CRUD + filtrage + recherche (même structure que production.py) :
  READ   -> lister()        SELECT avec OPTIONAL, BIND/IF, EXISTS, FILTER, CONTAINS, GROUP_CONCAT
  READ   -> obtenir()       SELECT sur un individu
  CREATE -> creer()         INSERT DATA (les deux sens de alimente / estAlimentePar)
  UPDATE -> modifier()      DELETE / INSERT WHERE
  DELETE -> supprimer()     DELETE WHERE
et des requêtes propres à la branche :
  gros_consommateurs() / alimentes_renouvelable()   classes définies recalculées par FILTER / EXISTS
  par_zone()                                        agrégats COUNT / SUM / AVG + GROUP BY
  carte()                                           tous les éléments par zone (carte Leaflet)
  classer()                                         applique les définitions OWL avec INSERT WHERE

Pourquoi classer() ? Le serveur SPARQL ne raisonne pas : HermiT a classé les individus de
l'ontologie, mais un bâtiment ajouté depuis l'appli n'aurait jamais le type GrosConsommateur.
classer() réécrit les deux définitions OWL sous forme de règles SPARQL (DELETE puis INSERT … WHERE).
"""
from fastapi import HTTPException

from ..sparql_client import client
from .common import changer_type, decimal, exists, renommer, safe_id, search_filter

TYPES = ["BatimentResidentiel", "BatimentCommercial", "BatimentIndustriel"]   # classes instanciables
SEUIL_GROS = 100000   # kWh, valeur de la définition de GrosConsommateur dans l'ontologie

# Motif réutilisé : « ?batiment est alimenté par au moins une source renouvelable »
_RENOUVELABLE = """EXISTS {{ {b} sg:estAlimentePar ?srcVerte .
                            ?srcVerte a/rdfs:subClassOf* sg:SourceRenouvelable }}"""


# ------------------------------------------------------------------ READ
def lister(type_: str | None = None, zone: str | None = None,
           min_kwh: float | None = None, max_kwh: float | None = None,
           recherche: str | None = None, alimente_par: str | None = None,
           gros: bool | None = None, renouvelable: bool | None = None) -> list[dict]:
    filtres = []
    if type_:
        if type_ not in TYPES:
            raise HTTPException(400, f"Type inconnu : {type_}")
        filtres.append(f"?batiment a sg:{type_} .")
    if zone:
        filtres.append(f"?batiment sg:estSitueDans sg:{safe_id(zone)} .")
    if alimente_par:
        filtres.append(f"?batiment sg:estAlimentePar sg:{safe_id(alimente_par)} .")
    if min_kwh is not None:
        filtres.append(f"FILTER(?consommation >= {float(min_kwh)})")
    if max_kwh is not None:
        filtres.append(f"FILTER(?consommation <= {float(max_kwh)})")
    if gros is not None:
        filtres.append(f"FILTER(?gros = {int(gros)})")
    if renouvelable is not None:
        filtres.append(f"FILTER(?renouvelable = {int(renouvelable)})")
    filtres.append(search_filter("?batiment", recherche))

    # ?gros et ?renouvelable sont recalculés à chaque lecture (1 / 0) : ils sont donc justes
    # aussi pour un bâtiment ajouté depuis l'appli, que HermiT n'a jamais vu.
    q = f"""
    SELECT ?batiment ?type ?consommation ?zone ?gros ?renouvelable
           (GROUP_CONCAT(DISTINCT STRAFTER(STR(?src), "#"); separator=", ") AS ?alimentePar)
    WHERE {{
        ?batiment a ?type .
        VALUES ?type {{ {' '.join('sg:' + t for t in TYPES)} }}
        OPTIONAL {{ ?batiment sg:consommationKWh ?consommation }}
        OPTIONAL {{ ?batiment sg:estSitueDans ?zone }}
        OPTIONAL {{ ?batiment sg:estAlimentePar ?src }}
        BIND(IF(COALESCE(?consommation, 0) >= {SEUIL_GROS}, 1, 0) AS ?gros)
        BIND(IF({_RENOUVELABLE.format(b='?batiment')}, 1, 0) AS ?renouvelable)
        {' '.join(filtres)}
    }}
    GROUP BY ?batiment ?type ?consommation ?zone ?gros ?renouvelable
    ORDER BY DESC(?consommation)"""
    return client.select(q)


def obtenir(nom: str) -> dict:
    nom = safe_id(nom)
    rows = [r for r in lister() if r["batiment"] == nom]
    if not rows:
        raise HTTPException(404, f"Bâtiment introuvable : {nom}")
    return rows[0]


def gros_consommateurs(seuil: float = SEUIL_GROS) -> list[dict]:
    """Équivalent SPARQL de la classe définie GrosConsommateur (seuil réglable)."""
    q = f"""
    SELECT ?batiment ?type ?consommation ?zone WHERE {{
        ?batiment a ?type ;
                  sg:consommationKWh ?consommation .
        VALUES ?type {{ {' '.join('sg:' + t for t in TYPES)} }}
        OPTIONAL {{ ?batiment sg:estSitueDans ?zone }}
        FILTER(?consommation >= {float(seuil)})
    }} ORDER BY DESC(?consommation)"""
    return client.select(q)


def alimentes_renouvelable() -> list[dict]:
    """Équivalent SPARQL de BatimentAlimenteRenouvelable, avec la source verte qui alimente."""
    q = f"""
    SELECT ?batiment ?consommation ?zone
           (GROUP_CONCAT(DISTINCT STRAFTER(STR(?src), "#"); separator=", ") AS ?sourcesVertes)
    WHERE {{
        ?batiment a/rdfs:subClassOf* sg:BatimentConsommateur ;
                  sg:estAlimentePar ?src .
        ?src a/rdfs:subClassOf* sg:SourceRenouvelable .
        OPTIONAL {{ ?batiment sg:consommationKWh ?consommation }}
        OPTIONAL {{ ?batiment sg:estSitueDans ?zone }}
    }}
    GROUP BY ?batiment ?consommation ?zone
    ORDER BY DESC(?consommation)"""
    return client.select(q)


def par_zone() -> list[dict]:
    """Bilan par zone : nombre de bâtiments, consommation totale / moyenne, part renouvelable."""
    q = f"""
    SELECT ?zone (COUNT(?batiment) AS ?nombre) (SUM(?c) AS ?total) (AVG(?c) AS ?moyenne)
           (SUM(?vert) AS ?nbRenouvelable)
    WHERE {{
        ?batiment a ?type ;
                  sg:estSitueDans ?zone .
        VALUES ?type {{ {' '.join('sg:' + t for t in TYPES)} }}
        OPTIONAL {{ ?batiment sg:consommationKWh ?conso }}
        BIND(COALESCE(?conso, 0) AS ?c)
        BIND(IF({_RENOUVELABLE.format(b='?batiment')}, 1, 0) AS ?vert)
    }}
    GROUP BY ?zone
    ORDER BY DESC(?total)"""
    return client.select(q)


def carte() -> list[dict]:
    """Tous les composants du smart grid avec leur zone et leur branche (pour la carte)."""
    q = """
    SELECT DISTINCT ?element ?zone ?branche ?consommation WHERE {
        VALUES ?branche { sg:SourceProduction sg:SystemeStockage
                          sg:BatimentConsommateur sg:InfrastructureReseau }
        ?element a/rdfs:subClassOf* ?branche ;
                 sg:estSitueDans ?zone .
        OPTIONAL { ?element sg:consommationKWh ?consommation }
    } ORDER BY ?zone ?branche ?element"""
    return client.select(q)


def fournisseurs() -> list[dict]:
    """Ce qui peut alimenter un bâtiment : codomaine de estAlimentePar (source ou stockage)."""
    q = """
    SELECT DISTINCT ?element ?branche WHERE {
        VALUES ?branche { sg:SourceProduction sg:SystemeStockage }
        ?element a/rdfs:subClassOf* ?branche .
    } ORDER BY ?branche ?element"""
    return client.select(q)


def _verifier_fournisseurs(noms: list[str]) -> list[str]:
    """Respecte la restriction BatimentConsommateur ⊑ estAlimentePar some (Source ⊔ Stockage) :
    au moins un fournisseur, et chacun doit être une source ou un stockage existant."""
    noms = [safe_id(n) for n in noms]
    if not noms:
        raise HTTPException(400, "Un bâtiment doit être alimenté par au moins une source ou un stockage")
    valides = {r["element"] for r in fournisseurs()}
    inconnus = [n for n in noms if n not in valides]
    if inconnus:
        raise HTTPException(400, f"Pas une source ni un stockage : {', '.join(inconnus)}")
    return list(dict.fromkeys(noms))


# ------------------------------------------------------------------ CREATE
def creer(nom: str, type_: str, consommation: float, zone: str, alimente_par: list[str]) -> None:
    nom, zone = safe_id(nom), safe_id(zone)
    if type_ not in TYPES:
        raise HTTPException(400, f"Type invalide : {type_} (attendu : {TYPES})")
    if exists(nom):
        raise HTTPException(409, f"'{nom}' existe déjà")
    alimente_par = _verifier_fournisseurs(alimente_par)
    lignes = [f"sg:{nom} a owl:NamedIndividual , sg:{type_} ;",
              f"    sg:consommationKWh {decimal(consommation)} ;",
              f"    sg:estSitueDans sg:{zone} ."]
    for s in alimente_par:
        # on écrit les deux sens car le serveur SPARQL ne raisonne pas sur owl:inverseOf
        lignes.append(f"sg:{nom} sg:estAlimentePar sg:{s} . sg:{s} sg:alimente sg:{nom} .")
    client.update("INSERT DATA {\n" + "\n".join(lignes) + "\n}")
    classer()


# ------------------------------------------------------------------ UPDATE
def modifier(nom: str, consommation: float | None = None, zone: str | None = None,
             alimente_par: list[str] | None = None, type_: str | None = None,
             nouveau_nom: str | None = None) -> str:
    nom = safe_id(nom)
    if not any(r["batiment"] == nom for r in lister()):
        raise HTTPException(404, f"Bâtiment introuvable : {nom}")
    if nouveau_nom:
        safe_id(nouveau_nom)
    if type_:
        changer_type(nom, type_, TYPES)
    if consommation is not None:
        client.update(f"""
        DELETE {{ sg:{nom} sg:consommationKWh ?ancienne }}
        INSERT {{ sg:{nom} sg:consommationKWh {decimal(consommation)} }}
        WHERE  {{ OPTIONAL {{ sg:{nom} sg:consommationKWh ?ancienne }} }}""")
    if zone is not None:
        zone = safe_id(zone)
        client.update(f"""
        DELETE {{ sg:{nom} sg:estSitueDans ?ancienne }}
        INSERT {{ sg:{nom} sg:estSitueDans sg:{zone} }}
        WHERE  {{ OPTIONAL {{ sg:{nom} sg:estSitueDans ?ancienne }} }}""")
    if alimente_par is not None:
        alimente_par = _verifier_fournisseurs(alimente_par)
        # on remplace la liste : on retire les anciens liens (dans les deux sens), puis on ajoute
        client.update(f"DELETE WHERE {{ sg:{nom} sg:estAlimentePar ?s }}")
        client.update(f"DELETE WHERE {{ ?s sg:alimente sg:{nom} }}")
        client.update("INSERT DATA {\n" + "\n".join(
            f"sg:{nom} sg:estAlimentePar sg:{s} . sg:{s} sg:alimente sg:{nom} ."
            for s in alimente_par) + "\n}")
    resultat = renommer(nom, nouveau_nom) if nouveau_nom else nom   # en dernier
    classer()
    return resultat


# ------------------------------------------------------------------ DELETE
def supprimer(nom: str) -> None:
    nom = safe_id(nom)
    if not any(r["batiment"] == nom for r in lister()):
        raise HTTPException(404, f"Bâtiment introuvable : {nom}")
    # supprime les triplets où l'individu est sujet, puis ceux où il est objet (ex. alimente)
    client.update(f"DELETE WHERE {{ sg:{nom} ?p ?o }}")
    client.update(f"DELETE WHERE {{ ?s ?p sg:{nom} }}")


# ------------------------------------------------------------------ CLASSIFICATION
def classer() -> dict:
    """Applique les deux classes définies de l'ontologie avec SPARQL (le serveur ne raisonne pas).
    Une opération par appel : on efface l'ancien classement, puis on le recalcule."""
    batiment = "?b a/rdfs:subClassOf* sg:BatimentConsommateur ."
    client.update("DELETE WHERE { ?b a sg:GrosConsommateur }")
    client.update(f"""
    INSERT {{ ?b a sg:GrosConsommateur }}
    WHERE  {{ {batiment} ?b sg:consommationKWh ?c . FILTER(?c >= {SEUIL_GROS}) }}""")
    client.update("DELETE WHERE { ?b a sg:BatimentAlimenteRenouvelable }")
    client.update(f"""
    INSERT {{ ?b a sg:BatimentAlimenteRenouvelable }}
    WHERE  {{ {batiment} FILTER({_RENOUVELABLE.format(b='?b')}) }}""")
    compte = client.select("""
    SELECT ?classe (COUNT(?b) AS ?n) WHERE {
        VALUES ?classe { sg:GrosConsommateur sg:BatimentAlimenteRenouvelable }
        ?b a ?classe } GROUP BY ?classe""")
    return {r["classe"]: r["n"] for r in compte}
