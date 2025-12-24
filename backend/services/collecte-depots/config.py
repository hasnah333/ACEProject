"""
Configuration du service Collecte-Depots
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configuration du service."""
    
    # Base de données
    DATABASE_URL: str = "postgresql://ace_user:ace_password@localhost:5432/ace_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # GitHub
    GITHUB_TOKEN: Optional[str] = None
    
    # Services externes
    PRETRAITEMENT_URL: str = "http://localhost:8002"
    ML_SERVICE_URL: str = "http://localhost:8003"
    PRIORISATION_URL: str = "http://localhost:8004"
    ANALYSE_STATIQUE_URL: str = "http://localhost:8005"
    
    # Chemins
    REPOS_PATH: str = "./repos"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
