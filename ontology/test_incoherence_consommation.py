"""
Démonstration (branche CONSOMMATION) : HermiT vérifie les axiomes et classe les bâtiments.

    python ontology/test_incoherence_consommation.py

On charge SmartGrid.owl puis on ajoute, en mémoire seulement (le fichier n'est pas modifié),
des individus qui violent un axiome de la branche consommation :

  1. un bâtiment à la fois résidentiel et industriel
     -> DisjointClasses(BatimentResidentiel, BatimentCommercial, BatimentIndustriel)
  2. un bâtiment avec deux consommations différentes
     -> consommationKWh est une propriété fonctionnelle (une seule valeur)
  3. un bâtiment « alimenté par » une zone
     -> le codomaine de estAlimentePar est SourceProduction ⊔ SystemeStockage, donc HermiT
        déduit que la zone est un ComposantSmartGrid, or DisjointClasses(ComposantSmartGrid, Zone)

Puis un cas cohérent qui montre la CLASSIFICATION automatique (classes définies) :
  4. un hôpital de 300 000 kWh alimenté par la centrale solaire de Tozeur
     -> HermiT le range dans GrosConsommateur et dans BatimentAlimenteRenouvelable
"""
from pathlib import Path

from owlready2 import (OwlReadyInconsistentOntologyError, World, sync_reasoner_hermit)

SRC = Path(__file__).resolve().parent / "SmartGrid.owl"


def charger():
    world = World()
    return world, world.get_ontology(f"file://{SRC.as_posix()}").load()


def tester(titre: str, ajouter) -> None:
    world, onto = charger()
    with onto:
        ajouter(onto)
    try:
        with onto:
            sync_reasoner_hermit(world, debug=0)
        print(f"⚠️  {titre} : cohérente (l'axiome n'a pas joué)")
    except OwlReadyInconsistentOntologyError:
        print(f"✅ {titre} : incohérente, comme attendu")


def batiment_double_type(o):
    b = o.BatimentResidentiel("Batiment_Test", consommationKWh=5000.0, estSitueDans=o.Zone_Tunis,
                              estAlimentePar=[o.Centrale_Gaz_Rades])
    b.is_a.append(o.BatimentIndustriel)


def deux_consommations(o):
    # Residence_ElMenzah consomme déjà 12 000 kWh ; on affirme une seconde valeur
    o.Residence_ElMenzah.is_a.append(o.consommationKWh.value(99000.0))


def alimente_par_une_zone(o):
    o.Residence_ElMenzah.estAlimentePar.append(o.Zone_Tunis)


def classification():
    world, o = charger()
    with o:
        o.BatimentCommercial("Hopital_Sfax", consommationKWh=300000.0, estSitueDans=o.Zone_Sfax,
                             estAlimentePar=[o.Centrale_Solaire_Tozeur])
        sync_reasoner_hermit(world, infer_property_values=True, debug=0)
    classes = sorted(c.name for c in o.Hopital_Sfax.is_a if hasattr(c, "name"))
    attendu = {"GrosConsommateur", "BatimentAlimenteRenouvelable"}
    ok = "✅" if attendu <= set(classes) else "⚠️ "
    print(f"{ok} Hôpital de Sfax (300 000 kWh, solaire) classé par HermiT dans : {', '.join(classes)}")


if __name__ == "__main__":
    tester("Bâtiment à la fois résidentiel et industriel", batiment_double_type)
    tester("Bâtiment avec deux consommations", deux_consommations)
    tester("Bâtiment alimenté par une zone", alimente_par_une_zone)
    classification()
