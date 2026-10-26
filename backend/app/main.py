"""
Point d'entrée du backend.

    cd backend
    uvicorn app.main:app --reload

API      : http://localhost:8000/api/...
Doc API  : http://localhost:8000/docs   (Swagger, pratique pour tester chaque route)
Frontend : http://localhost:8000/       (servi directement par FastAPI)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import ROOT
from .routers import ask, common, consommation, production, reseau, stockage

app = FastAPI(title="SmartGrid — API Web sémantique", version="1.0")

# Autorise un front servi ailleurs (ex. Live Server sur le port 5500)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

for r in (common.router, production.router, stockage.router, consommation.router,
          reseau.router, ask.router):
    app.include_router(r)

# Le frontend est servi à la racine (à monter en dernier)
app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")
