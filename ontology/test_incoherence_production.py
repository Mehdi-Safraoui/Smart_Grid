"""
Démonstration (branche PRODUCTION — Mehdi) : HermiT vérifie les axiomes de la production.

    python ontology/test_incoherence_production.py

On charge SmartGrid.owl puis on ajoute, en mémoire seulement (le fichier n'est pas modifié),
des faits qui violent un axiome de la branche production :

  1. une source à la fois CentraleSolaire et ParcEolien
     -> DisjointClasses(CentraleSolaire, ParcEolien)
  2. une centrale solaire déclarée aussi SourceFossile
     -> CentraleSolaire ⊑ SourceRenouvelable et DisjointClasses(SourceRenouvelable, SourceFossile)
  3. une source avec deux puissances différentes
     -> puissanceMW est une propriété fonctionnelle (une seule valeur)
  4. une source qui « alimente » une zone
     -> le codomaine de alimente est BatimentConsommateur, disjoint de Zone
  5. une source fossile qui stocke de l'énergie
     -> le domaine de stockeEnergieDe est SystemeStockage, disjoint de SourceProduction

Puis un cas COHÉRENT qui montre la déduction : un nouveau bâtiment de 150 000 kWh alimenté
par la centrale solaire de Kairouan est classé automatiquement GrosConsommateur et
BatimentAlimenteRenouvelable (classes définies).
"""
from pathlib import Path

from owlready2 import OwlReadyInconsistentOntologyError, World, sync_reasoner_hermit

SRC = Path(__file__).resolve().parent / "SmartGrid.owl"


def charger():
    world = World()
    # as_uri() casse le chemin sous Windows : on construit l'URI à la main
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


def solaire_et_eolien(o):
    o.Centrale_Solaire_Kairouan.is_a.append(o.ParcEolien)


def solaire_et_fossile(o):
    o.Centrale_Solaire_Tozeur.is_a.append(o.SourceFossile)


def deux_puissances(o):
    # la centrale a déjà 450 MW ; on affirme en plus 500 MW
    o.Centrale_Gaz_Rades.is_a.append(o.puissanceMW.value(500.0))


def alimente_une_zone(o):
    o.Parc_Eolien_Bizerte.alimente.append(o.Zone_Tunis)


def source_qui_stocke(o):
    o.Centrale_Gaz_Sousse.stockeEnergieDe.append(o.Centrale_Gaz_Rades)


def classement_automatique() -> None:
    world, onto = charger()
    with onto:
        ecole = onto.BatimentCommercial("Ecole_Kairouan", consommationKWh=150000.0,
                                        estSitueDans=onto.Zone_Kairouan)
        onto.Centrale_Solaire_Kairouan.alimente.append(ecole)
        sync_reasoner_hermit(world, infer_property_values=True, debug=0)
    classes = sorted(c.name for c in ecole.is_a if hasattr(c, "name"))
    print(f"✅ École de Kairouan (150 000 kWh, solaire) classée par HermiT dans : "
          f"{', '.join(classes)}")
    print(f"   et HermiT déduit la relation inverse : estAlimentePar = "
          f"{[s.name for s in ecole.estAlimentePar]}")


if __name__ == "__main__":
    tester("Source à la fois solaire et éolienne", solaire_et_eolien)
    tester("Centrale solaire déclarée aussi fossile", solaire_et_fossile)
    tester("Source avec deux puissances différentes", deux_puissances)
    tester("Source qui alimente une zone", alimente_une_zone)
    tester("Source fossile qui stocke de l'énergie", source_qui_stocke)
    classement_automatique()
