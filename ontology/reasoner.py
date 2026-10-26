"""
Lance HermiT sur SmartGrid.owl :
  1. vérifie la cohérence (arrêt avec un message clair si incohérente) ;
  2. enregistre les déductions (relations inverses, classes parentes, classes définies)
     dans SmartGrid_inferred.owl, qui est chargé par le serveur SPARQL.

    python ontology/reasoner.py
Nécessite Java (HermiT est inclus dans owlready2).
"""
from pathlib import Path
import sys
from owlready2 import (World, sync_reasoner_hermit, OwlReadyInconsistentOntologyError)

HERE = Path(__file__).resolve().parent
SRC, OUT = HERE / "SmartGrid.owl", HERE / "SmartGrid_inferred.owl"

world = World()
onto = world.get_ontology(SRC.as_uri()).load()
try:
    with onto:  # les déductions sont ajoutées dans l'ontologie elle-même
        sync_reasoner_hermit(world, infer_property_values=True, debug=0)
except OwlReadyInconsistentOntologyError:
    sys.exit("❌ HermiT : ontologie INCOHÉRENTE. Vérifiez vos derniers ajouts "
             "(disjonctions, propriétés fonctionnelles, domaines/codomaines).")

bad = list(world.inconsistent_classes())
if bad:
    sys.exit(f"❌ Classes insatisfiables : {bad}")

onto.save(file=str(OUT), format="rdfxml")

# owlready2 n'écrit qu'un seul sens des propriétés inverses : on matérialise
# l'autre sens (déduit par HermiT) pour que les requêtes SPARQL le voient.
import rdflib
from rdflib.namespace import OWL
g = rdflib.Graph().parse(OUT)
for p, q in list(g.subject_objects(OWL.inverseOf)):
    for s, o in list(g.subject_objects(p)):
        g.add((o, q, s))
    for s, o in list(g.subject_objects(q)):
        g.add((o, p, s))
g.serialize(OUT, format="xml")

print("✅ HermiT : ontologie cohérente.")
print("   Gros consommateurs déduits :", [i.name for i in onto.GrosConsommateur.instances()])
print("   Bâtiments alimentés en renouvelable :",
      [i.name for i in onto.BatimentAlimenteRenouvelable.instances()])
print(f"   Version inférée enregistrée : {OUT.name}")
