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
    nouvelle = {"nom": "Centrale_Solaire_Kairouan", "type": "CentraleSolaire",
                "puissance": 100, "zone": "Zone_Tozeur", "alimente": ["Usine_Sfax"]}
    assert c.post("/api/production", json=nouvelle).status_code == 201
    assert c.post("/api/production", json=nouvelle).status_code == 409        # doublon
    noms = [s["source"] for s in c.get("/api/production", params={"min_mw": 50}).json()]
    assert "Centrale_Solaire_Kairouan" in noms
    assert c.put("/api/production/Centrale_Solaire_Kairouan", json={"puissance": 120}).status_code == 200
    assert c.get("/api/production/Centrale_Solaire_Kairouan").json()["puissance"] == 120
    # le NLP reconnaît immédiatement le nouvel individu et la relation inverse
    r = ask("Qui alimente l'usine de Sfax ?")
    assert "Centrale_Solaire_Kairouan" in {x["sujet"] for x in r["resultats"]}
    assert c.delete("/api/production/Centrale_Solaire_Kairouan").status_code == 200
    assert c.get("/api/production/Centrale_Solaire_Kairouan").status_code == 404


def test_production_recherche_et_injection():
    assert c.get("/api/production", params={"recherche": "tozeur"}).json()[0]["source"] \
        == "Centrale_Solaire_Tozeur"
    assert c.post("/api/production", json={"nom": "x} ; DROP ALL ; {", "type": "CentraleSolaire",
                                           "puissance": 1, "zone": "Zone_Tunis"}).status_code == 400


# ----------------------------------------------------------------- NLP
@pytest.mark.parametrize("question, attendu", [
    ("Quelles sont les centrales solaires ?", {"Centrale_Solaire_Tozeur"}),
    ("Quelles sources produisent plus de 50 MW ?", {"Centrale_Gaz_Rades", "Parc_Eolien_SidiDaoud"}),
    ("Quelle est la source la plus puissante ?", {"Centrale_Gaz_Rades"}),
    ("Quels bâtiments consomment plus de 100 000 kWh ?", {"Usine_Sfax", "Centre_Commercial_Tunis"}),
    ("Liste les sources renouvelables à Tozeur", {"Centrale_Solaire_Tozeur"}),
    ("Quelles lignes ont une tension supérieure à 100 kV ?", {"Ligne_Rades_Tunis", "Ligne_Tozeur_Sfax"}),
    ("Quels sont les gros consommateurs ?", {"Usine_Sfax", "Centre_Commercial_Tunis"}),
])
def test_nlp_listes(question, attendu):
    r = ask(question)
    assert r["erreur"] is None
    assert {x["element"] for x in r["resultats"]} == attendu


def test_nlp_comptage_relation_detail():
    assert ask("Combien de bâtiments y a-t-il à Tunis ?")["resultats"] == [{"nombre": 2}]
    assert {x["sujet"] for x in ask("Qui alimente l'usine de Sfax ?")["resultats"]} \
        == {"Centrale_Solaire_Tozeur", "Batterie_Tozeur"}
    assert {x["objet"] for x in ask("Quels bâtiments sont alimentés par le parc éolien ?")["resultats"]} \
        == {"Centre_Commercial_Tunis"}
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
        == {"Parc_Eolien_SidiDaoud"}


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
