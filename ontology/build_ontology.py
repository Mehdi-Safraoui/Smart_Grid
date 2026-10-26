"""
Génère l'ontologie SmartGrid (SmartGrid.owl) puis sa version inférée par HermiT
(SmartGrid_inferred.owl), qui est celle chargée dans le serveur SPARQL.

    python ontology/build_ontology.py

Vous pouvez aussi modifier directement SmartGrid.owl dans Protégé : dans ce cas,
lancez seulement  python ontology/reasoner.py  pour régénérer la version inférée.
Choisissez UNE des deux méthodes en équipe (Protégé OU ce script) pour éviter
d'écraser le travail des autres.
"""
from pathlib import Path
from owlready2 import *

HERE = Path(__file__).resolve().parent
onto = get_ontology("http://www.semanticweb.org/smartgrid/ontologie")

with onto:
    # =====================================================================
    # CLASSES (19 primitives + 2 définies)
    # Un seul critère de classement par niveau.
    # =====================================================================
    class ComposantSmartGrid(Thing): pass            # tout ce qui participe au smart grid

    # --- Branche PRODUCTION (selon l'origine de l'énergie) ---
    class SourceProduction(ComposantSmartGrid): pass
    class SourceRenouvelable(SourceProduction): pass
    class CentraleSolaire(SourceRenouvelable): pass
    class ParcEolien(SourceRenouvelable): pass
    class SourceFossile(SourceProduction): pass

    # --- Branche STOCKAGE (selon la technologie) ---
    class SystemeStockage(ComposantSmartGrid): pass
    class Batterie(SystemeStockage): pass
    class StockageHydrogene(SystemeStockage): pass

    # --- Branche CONSOMMATION (selon l'usage du bâtiment) ---
    class BatimentConsommateur(ComposantSmartGrid): pass
    class BatimentResidentiel(BatimentConsommateur): pass
    class BatimentCommercial(BatimentConsommateur): pass
    class BatimentIndustriel(BatimentConsommateur): pass

    # --- Branche RÉSEAU (infrastructure physique) ---
    class InfrastructureReseau(ComposantSmartGrid): pass
    class LigneElectrique(InfrastructureReseau): pass
    class LigneTransport(LigneElectrique): pass       # haute tension
    class LigneDistribution(LigneElectrique): pass    # moyenne / basse tension
    class PosteTransformation(InfrastructureReseau): pass

    # --- Localisation ---
    class Zone(Thing): pass

    # =====================================================================
    # OBJECT PROPERTIES (5)
    # =====================================================================
    class alimente(ObjectProperty):
        domain = [SourceProduction | SystemeStockage]; range = [BatimentConsommateur]
    class estAlimentePar(ObjectProperty):
        domain = [BatimentConsommateur]; range = [SourceProduction | SystemeStockage]
        inverse_property = alimente
    class stockeEnergieDe(ObjectProperty):
        domain = [SystemeStockage]; range = [SourceProduction]
    class relie(ObjectProperty):
        domain = [LigneElectrique]; range = [ComposantSmartGrid]
    class estSitueDans(ObjectProperty, FunctionalProperty):
        domain = [ComposantSmartGrid]; range = [Zone]

    # =====================================================================
    # DATA PROPERTIES (4)
    # =====================================================================
    class puissanceMW(DataProperty, FunctionalProperty):
        domain = [SourceProduction]; range = [float]
    class capaciteStockageMWh(DataProperty, FunctionalProperty):
        domain = [SystemeStockage]; range = [float]
    class consommationKWh(DataProperty, FunctionalProperty):
        domain = [BatimentConsommateur]; range = [float]
    class tensionKV(DataProperty, FunctionalProperty):
        domain = [LigneElectrique]; range = [float]

    # =====================================================================
    # AXIOMES
    # =====================================================================
    # 1) Restrictions (SubClassOf)
    ComposantSmartGrid.is_a.append(estSitueDans.some(Zone))
    SystemeStockage.is_a.append(stockeEnergieDe.some(SourceProduction))
    BatimentConsommateur.is_a.append(estAlimentePar.some(SourceProduction | SystemeStockage))
    LigneElectrique.is_a.append(relie.min(2, ComposantSmartGrid))

    # 2) Disjonctions (DisjointClasses)
    AllDisjoint([ComposantSmartGrid, Zone])
    AllDisjoint([SourceProduction, SystemeStockage, BatimentConsommateur, InfrastructureReseau])
    AllDisjoint([SourceRenouvelable, SourceFossile])
    AllDisjoint([CentraleSolaire, ParcEolien])
    AllDisjoint([Batterie, StockageHydrogene])
    AllDisjoint([BatimentResidentiel, BatimentCommercial, BatimentIndustriel])
    AllDisjoint([LigneElectrique, PosteTransformation])
    AllDisjoint([LigneTransport, LigneDistribution])

    # 3) Classes définies (EquivalentTo) : remplies automatiquement par HermiT
    class GrosConsommateur(BatimentConsommateur):
        equivalent_to = [BatimentConsommateur
                         & consommationKWh.some(ConstrainedDatatype(float, min_inclusive=100000.0))]
    class BatimentAlimenteRenouvelable(BatimentConsommateur):
        equivalent_to = [BatimentConsommateur & estAlimentePar.some(SourceRenouvelable)]

    # =====================================================================
    # INDIVIDUS DE BASE (chaque membre ajoute les siens dans sa branche)
    # =====================================================================
    tunis, nabeul, tozeur, sfax = (Zone("Zone_Tunis"), Zone("Zone_Nabeul"),
                                   Zone("Zone_Tozeur"), Zone("Zone_Sfax"))
    AllDifferent([tunis, nabeul, tozeur, sfax])

    # Production (Mehdi)
    solaire = CentraleSolaire("Centrale_Solaire_Tozeur", puissanceMW=10.0, estSitueDans=tozeur)
    eolien = ParcEolien("Parc_Eolien_SidiDaoud", puissanceMW=54.0, estSitueDans=nabeul)
    rades = SourceFossile("Centrale_Gaz_Rades", puissanceMW=450.0, estSitueDans=tunis)

    # Stockage (Mohamed Elyess)
    batt = Batterie("Batterie_Tozeur", capaciteStockageMWh=20.0,
                    stockeEnergieDe=[solaire], estSitueDans=tozeur)
    h2 = StockageHydrogene("Stockage_H2_SidiDaoud", capaciteStockageMWh=50.0,
                           stockeEnergieDe=[eolien], estSitueDans=nabeul)

    # Consommation (Ahmed Amine)
    res = BatimentResidentiel("Residence_ElMenzah", consommationKWh=12000.0, estSitueDans=tunis)
    com = BatimentCommercial("Centre_Commercial_Tunis", consommationKWh=250000.0, estSitueDans=tunis)
    usine = BatimentIndustriel("Usine_Sfax", consommationKWh=900000.0, estSitueDans=sfax)

    solaire.alimente = [usine]
    batt.alimente = [usine]
    eolien.alimente = [com]
    h2.alimente = [com]
    rades.alimente = [res]

    # Réseau (Yassine)
    posteSfax = PosteTransformation("Poste_Sfax", estSitueDans=sfax)
    posteTunis = PosteTransformation("Poste_Tunis", estSitueDans=tunis)
    LigneTransport("Ligne_Tozeur_Sfax", tensionKV=225.0, relie=[solaire, posteSfax], estSitueDans=sfax)
    LigneDistribution("Ligne_Poste_Usine_Sfax", tensionKV=30.0, relie=[posteSfax, usine], estSitueDans=sfax)
    LigneTransport("Ligne_Rades_Tunis", tensionKV=225.0, relie=[rades, posteTunis], estSitueDans=tunis)
    LigneDistribution("Ligne_Quartier_ElMenzah", tensionKV=0.4, relie=[posteTunis, res], estSitueDans=tunis)

    for e in list(onto.classes()) + list(onto.properties()):
        e.label = [locstr(e.name, "fr")]

onto.save(file=str(HERE / "SmartGrid.owl"), format="rdfxml")
print("SmartGrid.owl :", len(list(onto.classes())), "classes,",
      len(list(onto.object_properties())), "object properties,",
      len(list(onto.data_properties())), "data properties,",
      len(list(onto.individuals())), "individus")

if __name__ == "__main__":
    import subprocess, sys
    subprocess.run([sys.executable, str(HERE / "reasoner.py")], check=True)
