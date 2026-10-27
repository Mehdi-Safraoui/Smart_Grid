"""
VALEUR AJOUTÉE (branche Stockage — Mohamed Elyess) : le raisonneur HermiT dans l'application.

Le serveur SPARQL ne raisonne pas : un individu ajouté depuis l'appli n'est donc jamais
classé automatiquement (ex. un hôpital de 300 000 kWh n'apparaît pas comme GrosConsommateur).
Ce module :
  1. récupère toutes les données actuelles du serveur SPARQL (ontologie + ajouts du CRUD) ;
  2. lance HermiT dessus (via owlready2, comme ontology/reasoner.py) ;
  3. compare avant / après pour lister les NOUVELLES déductions :
       - classes déduites (classes définies GrosConsommateur, BatimentAlimenteRenouvelable,
         ou classe déduite d'un domaine / codomaine) ;
       - relations déduites (propriétés inverses : alimente <-> estAlimentePar) ;
  4. peut enregistrer ces déductions dans le serveur SPARQL (INSERT DATA), pour que les
     pages, la console et l'assistant NLP en profitent ;
  5. signale les incohérences (ex. un individu déclaré Batterie ET StockageHydrogene,
     alors que les deux classes sont disjointes).
"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF

from .config import NS, SPARQL_ENDPOINT
from .sparql_client import client, short

# Triplet ajouté pour la démonstration d'incohérence (jamais enregistré dans la base)
INCOHERENCE_DEMO = (URIRef(NS + "Batterie_Tozeur"), RDF.type, URIRef(NS + "StockageHydrogene"))


def _graphe_actuel() -> Graph:
    """Copie de toutes les données du serveur SPARQL (mode local ou Fuseki)."""
    g = Graph()
    if client.mode == "local":
        with client._lock:
            for t in client.graph:
                g.add(t)
        return g
    from SPARQLWrapper import SPARQLWrapper, XML
    sw = SPARQLWrapper(f"{SPARQL_ENDPOINT}/query")
    sw.setQuery("CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }")
    sw.setReturnFormat(XML)
    return sw.query().convert()


def _individus(g: Graph) -> set[URIRef]:
    return {s for s in g.subjects(RDF.type, OWL.NamedIndividual) if isinstance(s, URIRef)}


def _hermit(g: Graph) -> Graph:
    """Lance HermiT sur le graphe g et renvoie le graphe enrichi des déductions.
    Lève OwlReadyInconsistentOntologyError si l'ontologie est incohérente."""
    from owlready2 import World, sync_reasoner_hermit

    with tempfile.TemporaryDirectory() as tmp:
        src, out = Path(tmp) / "entree.owl", Path(tmp) / "sortie.owl"
        g.serialize(src, format="xml")
        world = World()
        onto = world.get_ontology(src.as_uri()).load()
        with onto:
            sync_reasoner_hermit(world, infer_property_values=True, debug=0)
        onto.save(file=str(out), format="rdfxml")
        res = Graph().parse(out)
    # owlready2 n'écrit qu'un seul sens des propriétés inverses : on matérialise l'autre
    for p, q in list(res.subject_objects(OWL.inverseOf)):
        for s, o in list(res.subject_objects(p)):
            res.add((o, q, s))
        for s, o in list(res.subject_objects(q)):
            res.add((o, p, s))
    return res


def _nouvelles_deductions(avant: Graph, apres: Graph) -> list[tuple]:
    """Triplets déduits par HermiT qui ne sont pas encore dans la base, limités aux
    individus (ABox) et au vocabulaire de l'ontologie SmartGrid."""
    individus = _individus(avant)
    nouveaux = []
    for s, p, o in apres:
        if s not in individus or (s, p, o) in avant or isinstance(o, Literal):
            continue
        if p == RDF.type and str(o).startswith(NS):
            nouveaux.append((s, p, o))
        elif str(p).startswith(NS) and o in individus:
            nouveaux.append((s, p, o))
    return sorted(nouveaux)


def _format(triplets: list[tuple]) -> list[dict]:
    lignes = []
    for s, p, o in triplets:
        genre = "classe" if p == RDF.type else "relation"
        lignes.append({"individu": short(str(s)),
                       "propriete": "a pour type" if genre == "classe" else short(str(p)),
                       "valeur": short(str(o)), "genre": genre})
    return lignes


def _membres(g: Graph, classe: str) -> list[str]:
    return sorted(short(str(s)) for s in g.subjects(RDF.type, URIRef(NS + classe)))


def raisonner(enregistrer: bool = False, tester_incoherence: bool = False) -> dict:
    """Point d'entrée appelé par la route /api/stockage/raisonner."""
    from owlready2 import OwlReadyInconsistentOntologyError

    debut = time.perf_counter()
    avant = _graphe_actuel()
    if tester_incoherence:
        avant.add(INCOHERENCE_DEMO)
    try:
        apres = _hermit(avant)
    except OwlReadyInconsistentOntologyError:
        return {
            "coherente": False,
            "message": ("HermiT : ontologie INCOHÉRENTE. "
                        + ("Test : Batterie_Tozeur a été déclarée aussi StockageHydrogene, or les "
                           "classes Batterie et StockageHydrogene sont disjointes (DisjointClasses). "
                           "Rien n'a été modifié dans la base." if tester_incoherence else
                           "Vérifiez les derniers ajouts : disjonctions, propriétés fonctionnelles "
                           "(une seule zone, une seule capacité), domaines / codomaines.")),
            "deductions": [], "classes_definies": {}, "enregistrees": 0,
            "duree_s": round(time.perf_counter() - debut, 2),
        }

    nouveaux = _nouvelles_deductions(avant, apres)
    if enregistrer and nouveaux and not tester_incoherence:
        corps = "\n".join(f"<{s}> <{p}> <{o}> ." for s, p, o in nouveaux)
        client.update("INSERT DATA {\n" + corps + "\n}")

    return {
        "coherente": True,
        "message": "HermiT : ontologie cohérente.",
        "deductions": _format(nouveaux),
        "classes_definies": {c: _membres(apres, c)
                             for c in ("GrosConsommateur", "BatimentAlimenteRenouvelable")},
        "enregistrees": len(nouveaux) if enregistrer and not tester_incoherence else 0,
        "duree_s": round(time.perf_counter() - debut, 2),
    }
