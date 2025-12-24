"""
Service Collecte-Depots
=======================
Service de collecte des données de dépôts Git (commits, fichiers, issues).
Port: 8001
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from config import settings
from database import init_db, close_db
from routers import repos, ml_proxy, health

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application."""
    logger.info("Starting Collecte-Depots service...")
    await init_db()
    yield
    logger.info("Shutting down Collecte-Depots service...")
    await close_db()


# Création de l'application FastAPI
app = FastAPI(
    title="ACE - Collecte Depots Service",
    description="Service de collecte des données de dépôts Git pour l'analyse prédictive de défauts",
    version="1.0.0",
    lifespan=lifespan,
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routers
app.include_router(health.router, tags=["Health"])
app.include_router(repos.router, prefix="/api/repos", tags=["Repositories"])
app.include_router(ml_proxy.router, prefix="/api/ml", tags=["ML Proxy"])


@app.get("/")
async def root():
    """Point d'entrée racine."""
    return {
        "service": "collecte-depots",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "repositories": "/api/repos",
            "ml_proxy": "/api/ml"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
