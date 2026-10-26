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
    ("Quelles sont les centrales solaires ?", {"Centrale_Solaire_Tozeur"}),
    ("Quelles sources produisent plus de 50 MW ?", {"Centrale_Gaz_Rades", "Parc_Eolien_SidiDaoud"}),
    ("Quelle est la source la plus puissante ?", {"Centrale_Gaz_Rades"}),
    ("Quels bâtiments consomment plus de 100 000 kWh ?", {"Usine_Sfax", "Centre_Commercial_Tunis"}),
    ("Liste les sources renouvelables à Tozeur", {"Centrale_Solaire_Tozeur"}),
    ("Quelles lignes ont une tension supérieure à 100 kV ?",
     {"Ligne_Rades_Tunis", "Ligne_Tozeur_Sfax", "Ligne_Kairouan_Sousse", "Ligne_Sfax_Sousse"}),
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
