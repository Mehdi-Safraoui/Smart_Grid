"""
Tests automatiques (mode local).   cd backend && python -m pytest -q
Chaque membre ajoute ici les tests de sa branche (CRUD + questions NLP).
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.sparql_client import client as sparql

c = TestClient(app)


@pytest.fixture(autouse=True)
def donnees_propres():
    sparql.reset()
    yield
    sparql.reset()


def ask(question):
    return c.post("/api/ask", json={"question": question}).json()


# ----------------------------------------------------------------- commun
def test_health_et_zones():
    assert c.get("/api/health").json()["status"] == "ok"
    assert "Zone_Tozeur" in c.get("/api/zones").json()


# ----------------------------------------------------------------- PRODUCTION (Mehdi)
def test_production_crud():
    nouvelle = {"nom": "Centrale_Solaire_Gafsa", "type": "CentraleSolaire",
                "puissance": 120, "zone": "Zone_Tozeur", "alimente": ["Usine_Sfax"]}
    assert c.post("/api/production", json=nouvelle).status_code == 201
    assert c.post("/api/production", json=nouvelle).status_code == 409        # doublon
    noms = [s["source"] for s in c.get("/api/production", params={"min_mw": 50}).json()]
    assert "Centrale_Solaire_Gafsa" in noms
    assert c.put("/api/production/Centrale_Solaire_Gafsa", json={"puissance": 150}).status_code == 200
    assert c.get("/api/production/Centrale_Solaire_Gafsa").json()["puissance"] == 150
    # le NLP reconnaît immédiatement le nouvel individu et la relation inverse
    r = ask("Qui alimente l'usine de Sfax ?")
    assert "Centrale_Solaire_Gafsa" in {x["sujet"] for x in r["resultats"]}
    assert c.delete("/api/production/Centrale_Solaire_Gafsa").status_code == 200
    assert c.get("/api/production/Centrale_Solaire_Gafsa").status_code == 404


def test_production_recherche_et_injection():
    assert c.get("/api/production", params={"recherche": "tozeur"}).json()[0]["source"] \
        == "Centrale_Solaire_Tozeur"
    assert c.post("/api/production", json={"nom": "x} ; DROP ALL ; {", "type": "CentraleSolaire",
                                           "puissance": 1, "zone": "Zone_Tunis"}).status_code == 400


# ----------------------------------------------------------------- RÉSEAU (Yassine)
def test_reseau_crud():
    nouvelle = {"nom": "Ligne_Kairouan_Sfax", "type": "LigneTransport", "zone": "Zone_Kairouan",
                "tension": 225, "relie": ["Poste_Kairouan", "Poste_Sfax"]}
    assert c.post("/api/reseau", json=nouvelle).status_code == 201
    assert c.post("/api/reseau", json=nouvelle).status_code == 409             # doublon
    noms = [e["element"] for e in c.get("/api/reseau", params={"min_kv": 200}).json()]
    assert "Ligne_Kairouan_Sfax" in noms
    assert c.put("/api/reseau/Ligne_Kairouan_Sfax",
                 json={"tension": 400, "relie": ["Poste_Kairouan", "Poste_Sousse"]}).status_code == 200
    ligne = c.get("/api/reseau/Ligne_Kairouan_Sfax").json()
    assert ligne["tension"] == 400 and set(ligne["relie"].split(", ")) == {"Poste_Kairouan", "Poste_Sousse"}
    # le NLP reconnaît immédiatement la nouvelle ligne
    r = ask("Quelles lignes relient le poste de Kairouan ?")
    assert {x["sujet"] for x in r["resultats"]} == {"Ligne_Kairouan_Sousse", "Ligne_Kairouan_Sfax"}
    assert c.delete("/api/reseau/Ligne_Kairouan_Sfax").status_code == 200
    assert c.get("/api/reseau/Ligne_Kairouan_Sfax").status_code == 404


def test_reseau_filtres():
    def noms(**params):
        return {e["element"] for e in c.get("/api/reseau", params=params).json()}
    assert noms(type="PosteTransformation") == {"Poste_Sfax", "Poste_Tunis", "Poste_Kairouan",
                                                "Poste_Sousse"}
    assert noms(type="LigneDistribution", max_kv=1) == {"Ligne_Quartier_ElMenzah", "Ligne_Quartier_Sfax"}
    assert noms(zone="Zone_Sousse") == {"Poste_Sousse", "Ligne_Sfax_Sousse"}
    assert noms(relie_a="Usine_Sfax") == {"Ligne_Poste_Usine_Sfax", "Ligne_Quartier_Sfax"}
    assert noms(recherche="kairouan") == {"Poste_Kairouan", "Ligne_Kairouan_Sousse"}
    assert c.get("/api/reseau", params={"type": "Batterie"}).status_code == 400


def test_reseau_axiomes():
    # restriction « relie min 2 » : une ligne qui ne relie qu'un élément est refusée
    assert c.post("/api/reseau", json={"nom": "Ligne_X", "type": "LigneDistribution",
                                       "zone": "Zone_Sfax", "tension": 30,
                                       "relie": ["Poste_Sfax"]}).status_code == 400
    # composant inexistant
    assert c.post("/api/reseau", json={"nom": "Ligne_X", "type": "LigneDistribution",
                                       "zone": "Zone_Sfax", "tension": 30,
                                       "relie": ["Poste_Sfax", "Poste_Inconnu"]}).status_code == 400
    # domaine de tensionKV = LigneElectrique, disjointe de PosteTransformation
    assert c.post("/api/reseau", json={"nom": "Poste_X", "type": "PosteTransformation",
                                       "zone": "Zone_Sfax", "tension": 225}).status_code == 400
    assert c.put("/api/reseau/Poste_Sfax", json={"tension": 225}).status_code == 400
    # injection SPARQL
    assert c.post("/api/reseau", json={"nom": "x} ; DROP ALL ; {", "type": "PosteTransformation",
                                       "zone": "Zone_Sfax"}).status_code == 400
    # supprimer un poste signale les lignes qui ne relient plus qu'un élément
    r = c.delete("/api/reseau/Poste_Kairouan").json()
    assert r["lignes_incompletes"] == ["Ligne_Kairouan_Sousse"]


def test_reseau_parcours():
    r = c.get("/api/reseau/parcours",
              params={"depart": "Centrale_Solaire_Tozeur", "arrivee": "Usine_Sfax"}).json()
    assert [e["element"] for e in r] == ["Centrale_Solaire_Tozeur", "Ligne_Tozeur_Sfax", "Poste_Sfax",
                                         "Ligne_Poste_Usine_Sfax", "Usine_Sfax"]
    assert r[1]["type"] == "LigneTransport" and r[1]["tension"] == 225
    assert c.get("/api/reseau/parcours", params={"depart": "Centrale_Gaz_Rades",
                                                 "arrivee": "Poste_Kairouan"}).status_code == 404


@pytest.mark.parametrize("question, cle, attendu", [
    ("Quelles sont les lignes de distribution ?", "element",
     {"Ligne_Poste_Usine_Sfax", "Ligne_Quartier_ElMenzah", "Ligne_Quartier_Sfax"}),
    ("Qu'est-ce que relie la ligne Tozeur Sfax ?", "objet", {"Centrale_Solaire_Tozeur", "Poste_Sfax"}),
    ("Quelles lignes sont reliées au poste de Sousse ?", "sujet",
     {"Ligne_Kairouan_Sousse", "Ligne_Sfax_Sousse"}),
    ("Quelles lignes connectent la centrale solaire de Tozeur ?", "sujet", {"Ligne_Tozeur_Sfax"}),
    ("Quelle ligne a la tension la plus faible ?", "element", {"Ligne_Quartier_ElMenzah",
                                                             "Ligne_Quartier_Sfax"}),
    ("Quels sont les postes de transformation à Sousse ?", "element", {"Poste_Sousse"}),
    ("Qu'est-ce qu'il y a à Sfax ?", "element",
     {"Usine_Sfax", "Poste_Sfax", "Ligne_Tozeur_Sfax", "Ligne_Poste_Usine_Sfax", "Ligne_Quartier_Sfax"}),
])
def test_nlp_reseau(question, cle, attendu):
    r = ask(question)
    assert r["erreur"] is None
    resultats = {x[cle] for x in r["resultats"]}
    # superlatif : une seule réponse, parmi les ex aequo
    assert resultats <= attendu if "plus" in question else resultats == attendu


def test_nlp_reseau_comptage():
    assert ask("Combien de postes y a-t-il ?")["resultats"] == [{"nombre": 4}]
    assert ask("Combien de lignes relient le poste de Sfax ?")["resultats"] == [{"nombre": 4}]


# ----------------------------------------------------------------- NLP
@pytest.mark.parametrize("question, attendu", [
    ("Quelles sources produisent plus de 50 MW ?", {"Centrale_Gaz_Rades", "Centrale_Gaz_Sousse",
     "Centrale_Solaire_Kairouan", "Parc_Eolien_Bizerte", "Parc_Eolien_SidiDaoud"}),
    ("Quelle est la source la plus puissante ?", {"Centrale_Gaz_Rades"}),
    ("Quels bâtiments consomment plus de 100 000 kWh ?",
     {"Usine_Sfax", "Centre_Commercial_Tunis", "Hotel_Nabeul", "Usine_Textile_Nabeul"}),
    ("Liste les sources renouvelables à Tozeur", {"Centrale_Solaire_Tozeur"}),
    ("Quelles lignes ont une tension supérieure à 100 kV ?",
     {"Ligne_Rades_Tunis", "Ligne_Tozeur_Sfax", "Ligne_Kairouan_Sousse", "Ligne_Sfax_Sousse"}),
    ("Quels sont les gros consommateurs ?",
     {"Usine_Sfax", "Centre_Commercial_Tunis", "Hotel_Nabeul", "Usine_Textile_Nabeul"}),
])
def test_nlp_listes(question, attendu):
    r = ask(question)
    assert r["erreur"] is None
    assert {x["element"] for x in r["resultats"]} == attendu


def test_production_tableau_de_bord():
    d = c.get("/api/production/tableau-de-bord").json()
    assert d["total_mw"] == d["renouvelable_mw"] + d["fossile_mw"] == 1129
    assert d["part_renouvelable"] == 22.9
    assert {z["zone"] for z in d["par_zone"]} >= {"Zone_Kairouan", "Zone_Bizerte", "Zone_Sousse"}
    # le tableau de bord suit les modifications du CRUD
    c.post("/api/production", json={"nom": "Centrale_Solaire_Gafsa", "type": "CentraleSolaire",
                                    "puissance": 120, "zone": "Zone_Tozeur"})
    assert c.get("/api/production/tableau-de-bord").json()["renouvelable_mw"] == 379


# ----------------------------------------------------------------- NLP PRODUCTION (Mehdi)
@pytest.mark.parametrize("question, attendu", [
    ("Quelles sont les centrales solaires ?", {"Centrale_Solaire_Tozeur", "Centrale_Solaire_Kairouan"}),
    ("Quels parcs éoliens produisent plus de 60 MW ?", {"Parc_Eolien_Bizerte"}),
    ("Quelle est la source renouvelable la plus puissante ?", {"Centrale_Solaire_Kairouan"}),
    ("Quelle est la source la moins puissante ?", {"Centrale_Solaire_Tozeur"}),
    ("Quelles sources ont une puissance entre 50 et 200 MW ?",
     {"Centrale_Solaire_Kairouan", "Parc_Eolien_Bizerte", "Parc_Eolien_SidiDaoud"}),
    ("Quelles sources fossiles y a-t-il ?", {"Centrale_Gaz_Rades", "Centrale_Gaz_Sousse"}),
    ("Quelles centrales se trouvent à Bizerte ?", {"Parc_Eolien_Bizerte"}),
])
def test_nlp_production(question, attendu):
    r = ask(question)
    assert r["erreur"] is None
    assert {x["element"] for x in r["resultats"]} == attendu


def test_nlp_production_comptage_et_relations():
    assert ask("Combien de sources renouvelables y a-t-il ?")["resultats"] == [{"nombre": 4}]
    assert {x["objet"] for x in ask("Qu'alimente la centrale solaire de Kairouan ?")["resultats"]} \
        == {"Usine_Sfax"}
    assert {x["objet"] for x in ask("Qu'alimente le parc éolien de Bizerte ?")["resultats"]} \
        == {"Hotel_Nabeul"}


# ----------------------------------------------------------------- NLP REGROUPEMENT (Mehdi)
def test_nlp_regroupement():
    r = ask("Quelle est la puissance installée par zone ?")
    assert r["analyse"]["intention"] == "regroupement" and "GROUP BY ?zone" in r["sparql"]
    assert {x["zone"]: x["total"] for x in r["resultats"]} == {
        "Zone_Tunis": 450, "Zone_Sousse": 420, "Zone_Kairouan": 100,
        "Zone_Bizerte": 95, "Zone_Nabeul": 54, "Zone_Tozeur": 10}
    assert {x["type"]: x["nombre"] for x in ask("Combien de sources par type ?")["resultats"]} == {
        "CentraleSolaire": 2, "ParcEolien": 2, "SourceFossile": 2}
    assert {x["type"]: x["moyenne"] for x in
            ask("Quelle est la puissance moyenne des sources par type ?")["resultats"]} == {
        "SourceFossile": 435, "ParcEolien": 74.5, "CentraleSolaire": 55}
    # filtre de classe + pluriel (« sources renouvelables ») : aucune zone fossile
    zones = {x["zone"] for x in ask("Combien de sources renouvelables par zone ?")["resultats"]}
    assert zones == {"Zone_Kairouan", "Zone_Tozeur", "Zone_Bizerte", "Zone_Nabeul"}
    # un bâtiment à plusieurs types (industriel + gros consommateur) n'est compté qu'une fois
    conso = {x["zone"]: (x["total"], x["nombre"])
             for x in ask("Quelle est la consommation totale par zone ?")["resultats"]}
    assert conso["Zone_Sfax"] == (900000, 1) and conso["Zone_Tunis"] == (307000, 3)
    assert {x["type"] for x in ask("Répartition des stockages")["resultats"]} == {
        "Batterie", "StockageHydrogene"}
    # non-régression : sans « par … », la question reste une liste / un superlatif
    assert ask("Quelle est la source la plus puissante ?")["analyse"]["intention"] == "superlatif"
    assert ask("Quelles sont les zones ?")["analyse"]["intention"] == "liste"


def test_nlp_comptage_relation_detail():
    assert ask("Combien de bâtiments y a-t-il à Tunis ?")["resultats"] == [{"nombre": 3}]
    assert {x["sujet"] for x in ask("Qui alimente l'usine de Sfax ?")["resultats"]} \
        == {"Centrale_Solaire_Tozeur", "Centrale_Solaire_Kairouan", "Batterie_Tozeur"}
    assert {x["objet"] for x in ask("Quels bâtiments sont alimentés par le parc éolien ?")["resultats"]} \
        == {"Centre_Commercial_Tunis", "Hotel_Nabeul"}
    assert ask("Donne-moi des infos sur Radès")["analyse"]["intention"] == "detail"
    assert ask("Bonjour ça va ?")["erreur"]


# ----------------------------------------------------------------- STOCKAGE (Mohamed Elyess)
def test_stockage_crud():
    nouveau = {"nom": "Batterie_Sfax", "type": "Batterie", "capacite": 40,
               "zone": "Zone_Sfax", "stocke": ["Centrale_Solaire_Tozeur"], "alimente": ["Usine_Sfax"]}
    assert c.post("/api/stockage", json=nouveau).status_code == 201
    assert c.post("/api/stockage", json=nouveau).status_code == 409           # doublon
    # filtre capacité + filtre par source stockée
    noms = [s["stockage"] for s in c.get("/api/stockage", params={"min_mwh": 35, "max_mwh": 60}).json()]
    assert set(noms) == {"Batterie_Sfax", "Stockage_H2_SidiDaoud"}
    noms = [s["stockage"] for s in c.get("/api/stockage",
                                         params={"source": "Centrale_Solaire_Tozeur"}).json()]
    assert set(noms) == {"Batterie_Sfax", "Batterie_Tozeur", "Stockage_H2_Gabes"}
    # modification (DELETE / INSERT WHERE)
    assert c.put("/api/stockage/Batterie_Sfax",
                 json={"capacite": 45, "stocke": ["Parc_Eolien_SidiDaoud"]}).status_code == 200
    b = c.get("/api/stockage/Batterie_Sfax").json()
    assert b["capacite"] == 45 and b["stocke"] == "Parc_Eolien_SidiDaoud" and b["alimente"] == "Usine_Sfax"
    # scénario : l'assistant retrouve immédiatement la nouvelle batterie
    r = ask("Qui alimente l'usine de Sfax ?")
    assert "Batterie_Sfax" in {x["sujet"] for x in r["resultats"]}
    # suppression comme sujet ET comme objet (plus de « Usine_Sfax estAlimentePar Batterie_Sfax »)
    assert c.delete("/api/stockage/Batterie_Sfax").status_code == 200
    assert c.get("/api/stockage/Batterie_Sfax").status_code == 404
    assert "Batterie_Sfax" not in {x["valeur"] for x in c.get("/api/individu/Usine_Sfax").json()}


def test_stockage_validation_et_statistiques():
    base = {"nom": "Batterie_X", "type": "Batterie", "capacite": 10, "zone": "Zone_Sfax",
            "stocke": ["Centrale_Solaire_Tozeur"]}
    assert c.post("/api/stockage", json={**base, "type": "Volant"}).status_code == 400
    assert c.post("/api/stockage", json={**base, "stocke": []}).status_code == 422   # restriction OWL
    assert c.post("/api/stockage", json={**base, "nom": "x} ; DROP ALL ; {"}).status_code == 400
    assert c.get("/api/stockage", params={"recherche": "gabes"}).json()[0]["stockage"] == "Stockage_H2_Gabes"
    stats = {s["type"]: s for s in c.get("/api/stockage/statistiques").json()}
    assert stats["StockageHydrogene"]["totalMWh"] == 170 and stats["Batterie"]["nombre"] == 3


@pytest.mark.parametrize("question, attendu", [
    ("Quels stockages ont une capacité de plus de 30 MWh ?", {"Stockage_H2_Gabes", "Stockage_H2_SidiDaoud"}),
    ("Quel stockage a la plus grande capacité ?", {"Stockage_H2_Gabes"}),
    ("Quelle batterie a la plus petite capacité ?", {"Batterie_Tunis"}),
    ("Quels accumulateurs sont à Kairouan ?", {"Batterie_Kairouan"}),
])
def test_nlp_stockage_listes(question, attendu):
    r = ask(question)
    assert r["erreur"] is None
    assert {x["element"] for x in r["resultats"]} == attendu


def test_nlp_stockage_relation_et_comptage():
    assert ask("Combien de batteries y a-t-il ?")["resultats"] == [{"nombre": 3}]
    assert ask("Combien de stockages y a-t-il à Nabeul ?")["resultats"] == [{"nombre": 1}]
    r = ask("Quelle batterie stocke l'énergie de la centrale solaire de Tozeur ?")
    assert r["analyse"]["relation"] == "stockeEnergieDe"
    assert {x["sujet"] for x in r["resultats"]} == {"Batterie_Tozeur"}
    r = ask("Qu'est-ce qui est stocké par le stockage hydrogène ?")
    assert {x["objet"] for x in r["resultats"]} == {"Centrale_Solaire_Tozeur", "Parc_Eolien_SidiDaoud"}
    assert {x["objet"] for x in ask("Qu'est-ce qui est stocké par la batterie de Kairouan ?")["resultats"]} \
        == {"Centrale_Solaire_Kairouan"}


# ----------------------------------------------------------------- Valeur ajoutée : HermiT
def test_raisonneur_hermit():
    # un bâtiment ajouté « à la main » n'est pas classé : le serveur SPARQL ne raisonne pas
    sparql.update("""INSERT DATA { sg:Hopital_Sfax a owl:NamedIndividual , sg:BatimentCommercial ;
        sg:consommationKWh "300000.0"^^xsd:decimal ; sg:estSitueDans sg:Zone_Sfax .
        sg:Centrale_Solaire_Tozeur sg:alimente sg:Hopital_Sfax . }""")
    r = c.post("/api/stockage/raisonner", params={"enregistrer": True}).json()
    assert r["coherente"]
    deduits = {(d["individu"], d["valeur"]) for d in r["deductions"]}
    assert {("Hopital_Sfax", "GrosConsommateur"), ("Hopital_Sfax", "BatimentAlimenteRenouvelable"),
            ("Hopital_Sfax", "Centrale_Solaire_Tozeur")} <= deduits      # classes + relation inverse
    assert r["enregistrees"] == len(r["deductions"])
    # les déductions enregistrées sont visibles par l'assistant NLP
    gros = {x["element"] for x in ask("Quels sont les gros consommateurs ?")["resultats"]}
    assert "Hopital_Sfax" in gros
    # démonstration d'incohérence : Batterie ⊓ StockageHydrogene = ∅ (rien n'est modifié)
    r = c.post("/api/stockage/raisonner", params={"tester_incoherence": True}).json()
    assert r["coherente"] is False and "disjointes" in r["message"]
    assert c.get("/api/stockage/Batterie_Tozeur").json()["type"] == "Batterie"

# ----------------------------------------------------------------- CONSOMMATION (Ahmed Amine)
def batiments(**params):
    return {b["batiment"] for b in c.get("/api/consommation", params=params).json()}


def test_consommation_crud_scenario():
    # Scénario : un hôpital à Sfax (300 000 kWh) alimenté par la centrale solaire de Tozeur
    hopital = {"nom": "Hopital_Sfax", "type": "BatimentCommercial", "consommation": 300000,
               "zone": "Zone_Sfax", "alimente_par": ["Centrale_Solaire_Tozeur"]}
    assert c.post("/api/consommation", json=hopital).status_code == 201
    assert c.post("/api/consommation", json=hopital).status_code == 409         # doublon
    assert "Hopital_Sfax" in batiments(min_kwh=200000)
    h = c.get("/api/consommation/Hopital_Sfax").json()
    assert (h["gros"], h["renouvelable"], h["alimentePar"]) == (1, 1, "Centrale_Solaire_Tozeur")
    assert "Hopital_Sfax" in {b["batiment"] for b in c.get("/api/consommation/gros-consommateurs").json()}
    # relation inverse écrite dans les deux sens
    tozeur = c.get("/api/production/Centrale_Solaire_Tozeur").json()
    assert "Hopital_Sfax" in tozeur["alimente"]
    # classer() a donné les types des classes définies : le NLP le voit tout de suite
    assert "Hopital_Sfax" in {x["element"] for x in ask("Quels sont les gros consommateurs ?")["resultats"]}
    assert "Hopital_Sfax" in {x["element"] for x in ask("Quels sont les bâtiments verts ?")["resultats"]}
    assert {x["sujet"] for x in ask("Qui alimente l'hôpital de Sfax ?")["resultats"]} \
        == {"Centrale_Solaire_Tozeur"}
    # modification : moins de 100 000 kWh et alimenté par du gaz -> sort des deux classes
    maj = {"consommation": 50000, "alimente_par": ["Centrale_Gaz_Rades"]}
    assert c.put("/api/consommation/Hopital_Sfax", json=maj).status_code == 200
    h = c.get("/api/consommation/Hopital_Sfax").json()
    assert (h["consommation"], h["gros"], h["renouvelable"]) == (50000, 0, 0)
    assert "Hopital_Sfax" not in c.get("/api/production/Centrale_Solaire_Tozeur").json()["alimente"]
    assert "Hopital_Sfax" not in {x["element"] for x in ask("Quels sont les gros consommateurs ?")["resultats"]}
    assert c.delete("/api/consommation/Hopital_Sfax").status_code == 200
    assert c.get("/api/consommation/Hopital_Sfax").status_code == 404
    assert "Hopital_Sfax" not in c.get("/api/production/Centrale_Gaz_Rades").json()["alimente"]


def test_consommation_filtres():
    assert batiments(type="BatimentResidentiel") == {"Residence_ElMenzah", "Residence_Tozeur",
                                                     "Cite_Ennasr_Tunis"}
    assert batiments(zone="Zone_Nabeul") == {"Hotel_Nabeul", "Usine_Textile_Nabeul"}
    assert batiments(min_kwh=100000, max_kwh=200000) == {"Hotel_Nabeul", "Usine_Textile_Nabeul"}
    assert batiments(recherche="ennasr") == {"Cite_Ennasr_Tunis"}
    assert batiments(alimente_par="Centrale_Gaz_Rades") == {"Residence_ElMenzah", "Cite_Ennasr_Tunis"}
    assert batiments(gros=True, renouvelable=False) == {"Usine_Textile_Nabeul"}
    assert batiments(gros=False, renouvelable=True) == {"Residence_Tozeur"}
    assert c.get("/api/consommation", params={"type": "Batterie"}).status_code == 400
    bilan = {z["zone"]: z for z in c.get("/api/consommation/par-zone").json()}
    assert (bilan["Zone_Tunis"]["nombre"], bilan["Zone_Tunis"]["total"]) == (3, 307000)


def test_consommation_axiomes():
    base = {"nom": "Batiment_X", "type": "BatimentResidentiel", "consommation": 1000, "zone": "Zone_Tunis"}
    # restriction « estAlimentePar some (Source ⊔ Stockage) » : au moins un fournisseur
    assert c.post("/api/consommation", json=base).status_code == 400
    # codomaine de estAlimentePar : ni un bâtiment, ni une zone
    assert c.post("/api/consommation", json={**base, "alimente_par": ["Usine_Sfax"]}).status_code == 400
    assert c.post("/api/consommation", json={**base, "alimente_par": ["Zone_Tunis"]}).status_code == 400
    assert c.post("/api/consommation", json={**base, "type": "GrosConsommateur",
                                             "alimente_par": ["Centrale_Gaz_Rades"]}).status_code == 400
    # la route ne modifie / supprime que des bâtiments
    assert c.put("/api/consommation/Centrale_Gaz_Rades", json={"consommation": 1}).status_code == 404
    assert c.delete("/api/consommation/Centrale_Gaz_Rades").status_code == 404
    # injection SPARQL
    assert c.post("/api/consommation", json={**base, "nom": "x} ; DROP ALL ; {",
                                             "alimente_par": ["Centrale_Gaz_Rades"]}).status_code == 400


@pytest.mark.parametrize("question, cle, attendu", [
    ("Quel est le bâtiment qui consomme le plus ?", "element", {"Usine_Sfax"}),
    ("Quel bâtiment consomme le moins ?", "element", {"Residence_ElMenzah"}),
    ("Qui alimente le centre commercial ?", "sujet",
      {"Parc_Eolien_SidiDaoud", "Stockage_H2_SidiDaoud", "Batterie_Kairouan", "Stockage_H2_Gabes", "Centrale_Gaz_Sousse"}),
    ("Qui alimente l'hôtel de Nabeul ?", "sujet", {"Parc_Eolien_SidiDaoud", "Parc_Eolien_Bizerte"}),
    ("Qu'est-ce qui alimente l'usine textile ?", "sujet", {"Stockage_H2_SidiDaoud"}),
    ("Quels sont les bâtiments verts ?", "element",
     {"Usine_Sfax", "Centre_Commercial_Tunis", "Hotel_Nabeul", "Residence_Tozeur"}),
    ("Quels bâtiments dépendent de la centrale de Radès ?", "sujet",
     {"Residence_ElMenzah", "Cite_Ennasr_Tunis"}),
    ("Quels immeubles sont à Tozeur ?", "element", {"Residence_Tozeur"}),
    ("Quels hôtels consomment entre 100 000 et 200 000 kWh ?", "element", {"Hotel_Nabeul"}),
])
def test_nlp_consommation(question, cle, attendu):
    r = ask(question)
    assert r["erreur"] is None
    assert {x[cle] for x in r["resultats"]} == attendu


def test_nlp_consommation_agregats():
    assert ask("Combien de gros consommateurs y a-t-il ?")["resultats"] == [{"nombre": 4}]
    r = ask("Quelle est la consommation totale des bâtiments à Tunis ?")
    assert r["analyse"]["intention"] == "agregat"
    assert r["resultats"] == [{"total": 307000, "nombre": 3}]
    assert ask("Quelle est la consommation moyenne des bâtiments industriels ?")["resultats"] \
        == [{"moyenne": 525000, "nombre": 2}]
    # « moyenne tension » est une classe (ligne de distribution), pas une moyenne
    assert ask("Quelles sont les lignes de moyenne tension ?")["analyse"]["intention"] == "liste"


# ----------------------------------------------------------------- Modifier le nom et le type
def test_modifier_nom_et_type_stockage():
    # changement de type : Batterie -> StockageHydrogene (un seul type reste)
    assert c.put("/api/stockage/Batterie_Tozeur", json={"type": "StockageHydrogene"}).status_code == 200
    assert c.get("/api/stockage/Batterie_Tozeur").json()["type"] == "StockageHydrogene"
    assert c.put("/api/stockage/Batterie_Tozeur", json={"type": "Volant"}).status_code == 400
    # renommage : tous les liens suivent (comme sujet et comme objet)
    r = c.put("/api/stockage/Batterie_Tozeur", json={"nouveau_nom": "Stockage_Tozeur"})
    assert r.status_code == 200 and r.json()["nom"] == "Stockage_Tozeur"
    assert c.get("/api/stockage/Batterie_Tozeur").status_code == 404
    s = c.get("/api/stockage/Stockage_Tozeur").json()
    assert (s["capacite"], s["stocke"], set(s["alimente"].split(", "))) == \
        (20, "Centrale_Solaire_Tozeur", {"Usine_Sfax", "Residence_Tozeur"})
    assert "Stockage_Tozeur" in {x["valeur"] for x in c.get("/api/individu/Usine_Sfax").json()}
    assert "Batterie_Tozeur" not in {x["valeur"] for x in c.get("/api/individu/Usine_Sfax").json()}
    # nom déjà pris / invalide
    assert c.put("/api/stockage/Stockage_Tozeur", json={"nouveau_nom": "Batterie_Tunis"}).status_code == 409
    assert c.put("/api/stockage/Stockage_Tozeur", json={"nouveau_nom": "x} ; DROP ALL ; {"}).status_code == 400
    # remplacement des bâtiments alimentés
    assert c.put("/api/stockage/Stockage_Tozeur", json={"alimente": ["Hotel_Nabeul"]}).status_code == 200
    assert c.get("/api/stockage/Stockage_Tozeur").json()["alimente"] == "Hotel_Nabeul"


def test_modifier_nom_et_type_autres_branches():
    assert c.put("/api/production/Parc_Eolien_SidiDaoud",
                 json={"type": "CentraleSolaire", "nouveau_nom": "Centrale_Solaire_Nabeul"}).status_code == 200
    p = c.get("/api/production/Centrale_Solaire_Nabeul").json()
    assert p["type"] == "CentraleSolaire" and "Centre_Commercial_Tunis" in p["alimente"]
    assert "Centrale_Solaire_Nabeul" in c.get("/api/stockage/Stockage_H2_SidiDaoud").json()["stocke"]
    # consommation : le classement des classes définies est recalculé
    assert c.put("/api/consommation/Usine_Sfax",
                 json={"type": "BatimentCommercial", "nouveau_nom": "Centre_Sfax"}).status_code == 200
    b = c.get("/api/consommation/Centre_Sfax").json()
    assert b["type"] == "BatimentCommercial" and b["gros"] == 1
    # réseau : transport <-> distribution, mais pas poste <-> ligne
    assert c.put("/api/reseau/Ligne_Kairouan_Sousse", json={"type": "LigneDistribution"}).status_code == 200
    assert c.get("/api/reseau/Ligne_Kairouan_Sousse").json()["type"] == "LigneDistribution"
    assert c.put("/api/reseau/Poste_Sfax", json={"type": "LigneTransport"}).status_code == 400
    assert c.put("/api/reseau/Poste_Sfax", json={"nouveau_nom": "Poste_Sfax_Nord"}).status_code == 200
    assert "Poste_Sfax_Nord" in c.get("/api/reseau/Ligne_Sfax_Sousse").json()["relie"]
