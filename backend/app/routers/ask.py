"""Route du module NLP : question en langage naturel -> SPARQL -> résultats."""
from fastapi import APIRouter
from pydantic import BaseModel

from ..nlp.pipeline import traduire
from ..queries.common import list_zones
from ..sparql_client import client

router = APIRouter(prefix="/api", tags=["NLP"])


class Question(BaseModel):
    question: str


def _individus() -> list[str]:
    q = """SELECT DISTINCT ?i WHERE { ?i a ?c . ?c rdfs:subClassOf* sg:ComposantSmartGrid }"""
    return sorted(r["i"] for r in client.select(q))


@router.post("/ask")
def ask(q: Question):
    analyse = traduire(q.question, list_zones(), _individus())
    reponse = {
        "question": q.question,
        "analyse": {
            "tokens": analyse.tokens,
            "entites": [{k: v for k, v in e.items() if k != "debut"} for e in analyse.entites],
            "intention": analyse.intention,
            "filtres": analyse.filtres,
            "attribut": analyse.attribut,
            "relation": analyse.relation and analyse.relation["propriete"],
        },
        "sparql": analyse.sparql,
        "resultats": [],
        "erreur": analyse.erreur,
    }
    if analyse.sparql:
        try:
            reponse["resultats"] = client.select(analyse.sparql)
        except Exception as e:
            reponse["erreur"] = f"Erreur d'exécution SPARQL : {e}"
    return reponse
