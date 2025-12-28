"""
Configuration de la base de données PostgreSQL
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
import logging

from config import settings

logger = logging.getLogger(__name__)

# Conversion de l'URL pour asyncpg
DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Création du moteur async
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Classe de base pour les modèles SQLAlchemy."""
    pass


async def init_db():
    """Initialise la connexion à la base de données et crée les tables."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection established successfully")
        
        # Créer les tables si elles n'existent pas
        async with engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS repositories (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    url VARCHAR(500) NOT NULL UNIQUE,
                    provider VARCHAR(50) DEFAULT 'github',
                    default_branch VARCHAR(100) DEFAULT 'main',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_collected_at TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'active'
                )
            """))
            
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS commits (
                    id SERIAL PRIMARY KEY,
                    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
                    sha VARCHAR(100) NOT NULL,
                    message TEXT,
                    author_name VARCHAR(255),
                    author_email VARCHAR(255),
                    is_bugfix BOOLEAN DEFAULT FALSE,
                    committed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(repo_id, sha)
                )
            """))
            
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS file_metrics (
                    id SERIAL PRIMARY KEY,
                    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
                    file_id INTEGER,
                    filepath VARCHAR(500) NOT NULL,
                    commit_sha VARCHAR(100),
                    loc INTEGER DEFAULT 0,
                    sloc INTEGER DEFAULT 0,
                    comments INTEGER DEFAULT 0,
                    blank_lines INTEGER DEFAULT 0,
                    cyclomatic_complexity FLOAT DEFAULT 0,
                    max_cyclomatic_complexity FLOAT DEFAULT 0,
                    avg_cyclomatic_complexity FLOAT DEFAULT 0,
                    wmc FLOAT DEFAULT 0,
                    dit INTEGER DEFAULT 0,
                    noc INTEGER DEFAULT 0,
                    cbo INTEGER DEFAULT 0,
                    rfc INTEGER DEFAULT 0,
                    lcom FLOAT DEFAULT 0,
                    fan_in INTEGER DEFAULT 0,
                    fan_out INTEGER DEFAULT 0,
                    num_methods INTEGER DEFAULT 0,
                    num_classes INTEGER DEFAULT 0,
                    code_smells_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(repo_id, filepath, commit_sha)
                )
            """))
            
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS issues (
                    id SERIAL PRIMARY KEY,
                    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
                    github_id INTEGER,
                    title VARCHAR(500),
                    body TEXT,
                    state VARCHAR(50),
                    is_bug BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP
                )
            """))
            
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id SERIAL PRIMARY KEY,
                    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
                    filepath VARCHAR(500),
                    risk_score FLOAT,
                    is_defective BOOLEAN,
                    confidence FLOAT,
                    model_name VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS models (
                    id SERIAL PRIMARY KEY,
                    model_id VARCHAR(100) UNIQUE,
                    name VARCHAR(100),
                    model_type VARCHAR(50),
                    accuracy FLOAT,
                    precision_score FLOAT,
                    recall FLOAT,
                    f1_score FLOAT,
                    roc_auc FLOAT,
                    pr_auc FLOAT,
                    is_active BOOLEAN DEFAULT FALSE,
                    dataset_id INTEGER,
                    repo_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    model_path VARCHAR(500)
                )
            """))
            
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS datasets (
                    id SERIAL PRIMARY KEY,
                    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
                    name VARCHAR(255),
                    train_samples INTEGER,
                    test_samples INTEGER,
                    n_features INTEGER,
                    feature_names TEXT,
                    balancing_strategy VARCHAR(50),
                    temporal_split BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS files (
                    id SERIAL PRIMARY KEY,
                    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
                    commit_id INTEGER REFERENCES commits(id) ON DELETE CASCADE,
                    filepath VARCHAR(500) NOT NULL,
                    filename VARCHAR(255),
                    extension VARCHAR(20),
                    status VARCHAR(50),
                    additions INTEGER DEFAULT 0,
                    deletions INTEGER DEFAULT 0,
                    changes INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS code_smells (
                    id SERIAL PRIMARY KEY,
                    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
                    filepath VARCHAR(500),
                    smell_type VARCHAR(100),
                    severity VARCHAR(20),
                    line_start INTEGER,
                    line_end INTEGER,
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
        logger.info("Database tables created/verified successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def close_db():
    """Ferme la connexion à la base de données."""
    await engine.dispose()
    logger.info("Database connection closed")


async def get_db() -> AsyncSession:
    """Dépendance FastAPI pour obtenir une session de base de données."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
