"""
Service Prétraitement et Features
=================================
Service de génération de features pour le ML à partir des métriques de code.
Port: 8002
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import json
import os

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============ Configuration ============

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://ace_user:ace_password@localhost:5432/ace_db"
    REDIS_URL: str = "redis://localhost:6379"
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    DATASETS_PATH: str = "./datasets"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# Database
DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Pretraitement-Features service...")
    os.makedirs(settings.DATASETS_PATH, exist_ok=True)
    yield
    logger.info("Shutting down Pretraitement-Features service...")


# ============ Application FastAPI ============

app = FastAPI(
    title="ACE - Prétraitement Features Service",
    description="Service de génération de features pour la prédiction de défauts",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Schemas ============

class FeatureGenerationRequest(BaseModel):
    repo_id: int
    balancing_strategy: Optional[str] = "smote"  # none, smote, cost_sensitive
    use_temporal_split: Optional[bool] = True
    test_ratio: Optional[float] = 0.2


class FeatureGenerationResponse(BaseModel):
    dataset_id: int
    train_samples: int
    test_samples: int
    n_features: int
    message: str


class DatasetInfo(BaseModel):
    dataset_id: int
    train_samples: int
    test_samples: int
    n_features: int
    feature_names: List[str]
    created_at: str


# ============ Feature Names (selon le cahier de charges) ============

FEATURE_SCHEMA = [
    # Métriques CK
    {"name": "wmc", "type": "float", "description": "Weighted Methods per Class"},
    {"name": "dit", "type": "float", "description": "Depth of Inheritance Tree"},
    {"name": "noc", "type": "float", "description": "Number of Children"},
    {"name": "cbo", "type": "float", "description": "Coupling Between Objects"},
    {"name": "rfc", "type": "float", "description": "Response for a Class"},
    {"name": "lcom", "type": "float", "description": "Lack of Cohesion of Methods"},
    
    # Complexité cyclomatique (McCabe)
    {"name": "cyclomatic_complexity", "type": "float", "description": "Cyclomatic Complexity (McCabe)"},
    {"name": "max_cyclomatic_complexity", "type": "float", "description": "Max Cyclomatic Complexity"},
    {"name": "avg_cyclomatic_complexity", "type": "float", "description": "Avg Cyclomatic Complexity"},
    
    # Dépendances (in/out degree)
    {"name": "fan_in", "type": "int", "description": "Fan-in (In-degree)"},
    {"name": "fan_out", "type": "int", "description": "Fan-out (Out-degree)"},
    
    # Métriques de taille
    {"name": "loc", "type": "int", "description": "Lines of Code"},
    {"name": "sloc", "type": "int", "description": "Source Lines of Code"},
    {"name": "num_methods", "type": "int", "description": "Number of Methods"},
    {"name": "num_classes", "type": "int", "description": "Number of Classes"},
    
    # Code smells
    {"name": "code_smells_count", "type": "int", "description": "Code Smells Count"},
    
    # Métriques de changement
    {"name": "change_frequency", "type": "float", "description": "File Change Frequency"},
    {"name": "bug_history", "type": "int", "description": "Historical Bug Count"},
    {"name": "recent_changes", "type": "int", "description": "Recent Changes (last 30 days)"},
    {"name": "author_count", "type": "int", "description": "Number of Authors"},
]


# ============ Endpoints ============

@app.get("/")
async def root():
    return {
        "service": "pretraitement-features",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}


@app.get("/features/schema")
async def get_feature_schema():
    """Retourne le schéma des features utilisées."""
    return {"features": FEATURE_SCHEMA}


@app.post("/features/generate", response_model=FeatureGenerationResponse)
async def generate_features(request: FeatureGenerationRequest, db: AsyncSession = Depends(get_db)):
    """
    Génère les features pour l'entraînement ML à partir des métriques de code.
    Applique le balancement et le split temporel si demandé.
    """
    repo_id = request.repo_id
    
    # Vérifier que le repo existe
    result = await db.execute(
        text("SELECT id, name FROM repositories WHERE id = :id"),
        {"id": repo_id}
    )
    repo = result.fetchone()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    logger.info(f"Generating features for repo {repo_id}")
    
    try:
        # Récupérer les métriques de fichiers
        metrics_result = await db.execute(
            text("""
                SELECT 
                    fm.id, fm.filepath, fm.commit_sha,
                    fm.cyclomatic_complexity, fm.max_cyclomatic_complexity, fm.avg_cyclomatic_complexity,
                    fm.wmc, fm.dit, fm.noc, fm.cbo, fm.rfc, fm.lcom,
                    fm.fan_in, fm.fan_out,
                    fm.loc, fm.sloc, fm.num_methods, fm.num_classes,
                    fm.code_smells_count,
                    fm.created_at
                FROM file_metrics fm
                WHERE fm.repo_id = :repo_id
                ORDER BY fm.created_at
            """),
            {"repo_id": repo_id}
        )
        metrics_rows = metrics_result.fetchall()
        
        # Si pas de métriques, générer des données synthétiques pour démo
        if len(metrics_rows) == 0:
            logger.info(f"No metrics found, generating synthetic data for demo")
            return await generate_synthetic_dataset(db, repo_id, request)
        
        # Construire le DataFrame
        data = []
        for row in metrics_rows:
            data.append({
                "file_id": row[0],
                "filepath": row[1],
                "commit_sha": row[2],
                "cyclomatic_complexity": row[3] or 0,
                "max_cyclomatic_complexity": row[4] or 0,
                "avg_cyclomatic_complexity": row[5] or 0,
                "wmc": row[6] or 0,
                "dit": row[7] or 0,
                "noc": row[8] or 0,
                "cbo": row[9] or 0,
                "rfc": row[10] or 0,
                "lcom": row[11] or 0,
                "fan_in": row[12] or 0,
                "fan_out": row[13] or 0,
                "loc": row[14] or 0,
                "sloc": row[15] or 0,
                "num_methods": row[16] or 0,
                "num_classes": row[17] or 0,
                "code_smells_count": row[18] or 0,
                "created_at": row[19]
            })
        
        df = pd.DataFrame(data)
        
        # Ajouter les features de changement
        df = await add_change_features(db, df, repo_id)
        
        # Déterminer le label (is_buggy) basé sur l'historique des bugs
        df = await add_bug_labels(db, df, repo_id)
        
        # Split temporal ou random
        if request.use_temporal_split and len(df) > 10:
            split_idx = int(len(df) * (1 - request.test_ratio))
            train_df = df.iloc[:split_idx]
            test_df = df.iloc[split_idx:]
        else:
            from sklearn.model_selection import train_test_split
            train_df, test_df = train_test_split(df, test_size=request.test_ratio, random_state=42)
        
        # Appliquer le balancement sur les données d'entraînement
        if request.balancing_strategy == "smote" and len(train_df) > 5:
            train_df = apply_smote(train_df)
        
        # Sauvegarder le dataset
        dataset_id = await save_dataset(
            db, repo_id, train_df, test_df, 
            request.balancing_strategy, 
            request.use_temporal_split
        )
        
        feature_names = [f["name"] for f in FEATURE_SCHEMA]
        n_features = len([c for c in train_df.columns if c in feature_names])
        
        return FeatureGenerationResponse(
            dataset_id=dataset_id,
            train_samples=len(train_df),
            test_samples=len(test_df),
            n_features=n_features,
            message=f"Features generated successfully with {request.balancing_strategy} balancing"
        )
        
    except Exception as e:
        logger.error(f"Feature generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def generate_synthetic_dataset(db: AsyncSession, repo_id: int, request: FeatureGenerationRequest):
    """Génère un dataset synthétique pour la démonstration."""
    np.random.seed(42)
    n_samples = 200
    
    # Générer des features aléatoires mais réalistes
    data = {
        "file_id": range(n_samples),
        "filepath": [f"src/com/example/Class{i}.java" for i in range(n_samples)],
        "cyclomatic_complexity": np.random.exponential(5, n_samples) + 1,
        "max_cyclomatic_complexity": np.random.exponential(10, n_samples) + 1,
        "avg_cyclomatic_complexity": np.random.exponential(3, n_samples) + 1,
        "wmc": np.random.exponential(20, n_samples),
        "dit": np.random.randint(0, 6, n_samples),
        "noc": np.random.randint(0, 4, n_samples),
        "cbo": np.random.exponential(8, n_samples),
        "rfc": np.random.exponential(30, n_samples),
        "lcom": np.random.exponential(50, n_samples),
        "fan_in": np.random.randint(0, 15, n_samples),
        "fan_out": np.random.randint(0, 20, n_samples),
        "loc": np.random.exponential(200, n_samples).astype(int) + 10,
        "sloc": np.random.exponential(150, n_samples).astype(int) + 5,
        "num_methods": np.random.randint(1, 30, n_samples),
        "num_classes": np.random.randint(1, 5, n_samples),
        "code_smells_count": np.random.poisson(3, n_samples),
        "change_frequency": np.random.exponential(0.3, n_samples),
        "bug_history": np.random.poisson(1, n_samples),
        "recent_changes": np.random.poisson(2, n_samples),
        "author_count": np.random.randint(1, 8, n_samples),
    }
    
    df = pd.DataFrame(data)
    
    # Générer le label is_buggy basé sur les features (corrélation réaliste)
    bug_prob = (
        0.1 +
        0.02 * np.clip(df["cyclomatic_complexity"] / 10, 0, 1) +
        0.02 * np.clip(df["cbo"] / 20, 0, 1) +
        0.02 * np.clip(df["code_smells_count"] / 10, 0, 1) +
        0.01 * np.clip(df["change_frequency"], 0, 1) +
        0.02 * np.clip(df["bug_history"] / 5, 0, 1)
    )
    df["is_buggy"] = (np.random.random(n_samples) < bug_prob).astype(int)
    
    # Split
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()
    
    # Appliquer SMOTE si demandé
    if request.balancing_strategy == "smote":
        train_df = apply_smote(train_df)
    
    # Sauvegarder
    dataset_id = await save_dataset(
        db, repo_id, train_df, test_df,
        request.balancing_strategy,
        request.use_temporal_split
    )
    
    return FeatureGenerationResponse(
        dataset_id=dataset_id,
        train_samples=len(train_df),
        test_samples=len(test_df),
        n_features=len(FEATURE_SCHEMA),
        message="Synthetic dataset generated for demonstration"
    )


def apply_smote(df: pd.DataFrame) -> pd.DataFrame:
    """Applique SMOTE pour équilibrer les classes."""
    try:
        from imblearn.over_sampling import SMOTE
        
        feature_cols = [c for c in df.columns if c not in ["file_id", "filepath", "is_buggy", "commit_sha", "created_at"]]
        X = df[feature_cols].values
        y = df["is_buggy"].values
        
        # Vérifier qu'on a assez d'échantillons de chaque classe
        if y.sum() < 2 or (len(y) - y.sum()) < 2:
            return df
        
        smote = SMOTE(random_state=42, k_neighbors=min(5, y.sum() - 1))
        X_resampled, y_resampled = smote.fit_resample(X, y)
        
        # Reconstruire le DataFrame
        resampled_df = pd.DataFrame(X_resampled, columns=feature_cols)
        resampled_df["is_buggy"] = y_resampled
        resampled_df["file_id"] = range(len(resampled_df))
        resampled_df["filepath"] = [f"synthetic_{i}" for i in range(len(resampled_df))]
        
        return resampled_df
        
    except Exception as e:
        logger.warning(f"SMOTE failed: {e}, returning original data")
        return df


async def add_change_features(db: AsyncSession, df: pd.DataFrame, repo_id: int) -> pd.DataFrame:
    """Ajoute les features liées aux changements."""
    # Récupérer les statistiques de changement par fichier
    result = await db.execute(
        text("""
            SELECT filepath, COUNT(*) as change_count,
                   COUNT(DISTINCT author_name) as author_count
            FROM files f
            JOIN commits c ON f.commit_id = c.id
            WHERE f.repo_id = :repo_id
            GROUP BY filepath
        """),
        {"repo_id": repo_id}
    )
    changes = {row[0]: {"count": row[1], "authors": row[2]} for row in result.fetchall()}
    
    df["change_frequency"] = df["filepath"].map(lambda x: changes.get(x, {}).get("count", 0))
    df["author_count"] = df["filepath"].map(lambda x: changes.get(x, {}).get("authors", 1))
    df["recent_changes"] = df["change_frequency"] * 0.5  # Simplification
    df["bug_history"] = 0  # À enrichir avec l'historique réel
    
    return df


async def add_bug_labels(db: AsyncSession, df: pd.DataFrame, repo_id: int) -> pd.DataFrame:
    """Ajoute les labels is_buggy basés sur l'historique."""
    # Récupérer les fichiers modifiés dans des commits de bugfix
    result = await db.execute(
        text("""
            SELECT DISTINCT f.filepath
            FROM files f
            JOIN commits c ON f.commit_id = c.id
            WHERE f.repo_id = :repo_id AND c.is_bugfix = TRUE
        """),
        {"repo_id": repo_id}
    )
    buggy_files = {row[0] for row in result.fetchall()}
    
    df["is_buggy"] = df["filepath"].map(lambda x: 1 if x in buggy_files else 0)
    
    # Si pas assez de bugs, ajouter du bruit pour la démo
    if df["is_buggy"].sum() < 5:
        np.random.seed(42)
        noise_idx = np.random.choice(df.index, size=max(5, int(len(df) * 0.15)), replace=False)
        df.loc[noise_idx, "is_buggy"] = 1
    
    return df


async def save_dataset(
    db: AsyncSession, 
    repo_id: int, 
    train_df: pd.DataFrame, 
    test_df: pd.DataFrame,
    balancing_strategy: str,
    temporal_split: bool
) -> int:
    """Sauvegarde le dataset en base et sur disque."""
    
    feature_names = [f["name"] for f in FEATURE_SCHEMA]
    
    # Créer l'entrée en base
    result = await db.execute(
        text("""
            INSERT INTO datasets (repo_id, name, train_samples, test_samples, n_features, 
                                  feature_names, balancing_strategy, temporal_split)
            VALUES (:repo_id, :name, :train, :test, :n_feat, :feat_names, :bal, :temp)
            RETURNING id
        """),
        {
            "repo_id": repo_id,
            "name": f"dataset_repo_{repo_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "train": len(train_df),
            "test": len(test_df),
            "n_feat": len(feature_names),
            "feat_names": json.dumps(feature_names),
            "bal": balancing_strategy,
            "temp": temporal_split
        }
    )
    await db.commit()
    dataset_id = result.fetchone()[0]
    
    # Sauvegarder sur disque
    os.makedirs(settings.DATASETS_PATH, exist_ok=True)
    train_df.to_csv(f"{settings.DATASETS_PATH}/train_{dataset_id}.csv", index=False)
    test_df.to_csv(f"{settings.DATASETS_PATH}/test_{dataset_id}.csv", index=False)
    
    logger.info(f"Dataset {dataset_id} saved: {len(train_df)} train, {len(test_df)} test samples")
    
    return dataset_id


@app.get("/datasets", response_model=List[DatasetInfo])
async def list_datasets(db: AsyncSession = Depends(get_db)):
    """Liste tous les datasets générés."""
    result = await db.execute(
        text("SELECT id, train_samples, test_samples, n_features, feature_names, created_at FROM datasets ORDER BY created_at DESC")
    )
    rows = result.fetchall()
    
    datasets = []
    for row in rows:
        feat_names = row[4]
        if isinstance(feat_names, str):
            feat_names = json.loads(feat_names)
        elif feat_names is None:
            feat_names = []
            
        datasets.append(DatasetInfo(
            dataset_id=row[0],
            train_samples=row[1],
            test_samples=row[2],
            n_features=row[3],
            feature_names=feat_names,
            created_at=row[5].isoformat() if row[5] else ""
        ))
    return datasets


@app.get("/datasets/{dataset_id}", response_model=DatasetInfo)
async def get_dataset_info(dataset_id: int, db: AsyncSession = Depends(get_db)):
    """Récupère les informations d'un dataset."""
    result = await db.execute(
        text("""
            SELECT id, train_samples, test_samples, n_features, feature_names, created_at
            FROM datasets WHERE id = :id
        """),
        {"id": dataset_id}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    feat_names = row[4]
    if isinstance(feat_names, str):
        feat_names = json.loads(feat_names)
    elif feat_names is None:
        feat_names = []

    return DatasetInfo(
        dataset_id=row[0],
        train_samples=row[1],
        test_samples=row[2],
        n_features=row[3],
        feature_names=feat_names,
        created_at=row[5].isoformat() if row[5] else ""
    )


@app.get("/datasets/{dataset_id}/data")
async def get_dataset_data(dataset_id: int, split: str = "train"):
    """Récupère les données d'un dataset (train ou test)."""
    filepath = f"{settings.DATASETS_PATH}/{split}_{dataset_id}.csv"
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Dataset file not found: {filepath}")
    
    df = pd.read_csv(filepath)
    return {
        "dataset_id": dataset_id,
        "split": split,
        "samples": len(df),
        "columns": list(df.columns),
        "data": df.to_dict(orient="records")
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
