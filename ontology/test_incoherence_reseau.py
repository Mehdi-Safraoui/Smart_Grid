"""
Démonstration (branche RÉSEAU) : HermiT détecte une incohérence.

    python ontology/test_incoherence_reseau.py

On charge SmartGrid.owl puis on ajoute, en mémoire seulement (le fichier n'est pas modifié),
un individu qui viole un axiome de la branche réseau :

  1. un individu à la fois LigneTransport et LigneDistribution
     -> DisjointClasses(LigneTransport, LigneDistribution)
  2. un poste de transformation avec une tension (tensionKV)
     -> le domaine de tensionKV est LigneElectrique, donc HermiT déduit que le poste est
        une LigneElectrique, or DisjointClasses(LigneElectrique, PosteTransformation)
  3. une ligne située dans deux zones différentes
     -> estSitueDans est fonctionnelle et les zones sont toutes différentes (AllDifferent)

Chaque cas doit afficher « incohérente », ce qui montre que les axiomes sont bien vérifiés.
"""
from pathlib import Path

from owlready2 import (OwlReadyInconsistentOntologyError, World, sync_reasoner_hermit)

SRC = Path(__file__).resolve().parent / "SmartGrid.owl"


def tester(titre: str, ajouter) -> None:
    world = World()
    onto = world.get_ontology(SRC.as_uri()).load()
    with onto:
        ajouter(onto)
    try:
        with onto:
            sync_reasoner_hermit(world, debug=0)
        print(f"⚠️  {titre} : cohérente (l'axiome n'a pas joué)")
    except OwlReadyInconsistentOntologyError:
        print(f"✅ {titre} : incohérente, comme attendu")


def ligne_double_type(o):
    ligne = o.LigneTransport("Ligne_Test", tensionKV=90.0, estSitueDans=o.Zone_Sfax,
                             relie=[o.Poste_Sfax, o.Usine_Sfax])
    ligne.is_a.append(o.LigneDistribution)


def poste_avec_tension(o):
    o.Poste_Sfax.tensionKV = 225.0


def ligne_deux_zones(o):
    # la ligne est déjà dans Zone_Sfax ; on affirme qu'elle est aussi dans Zone_Tunis
    o.Ligne_Tozeur_Sfax.is_a.append(o.estSitueDans.value(o.Zone_Tunis))


if __name__ == "__main__":
    tester("Ligne à la fois transport et distribution", ligne_double_type)
    tester("Poste de transformation avec une tension", poste_avec_tension)
    tester("Ligne située dans deux zones", ligne_deux_zones)
