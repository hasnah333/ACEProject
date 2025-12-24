"""
Router proxy pour les services ML
Permet au frontend de communiquer avec les services ML via le backend principal
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import httpx
import logging

from database import get_db
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ============ Schemas ============

class PredictRequest(BaseModel):
    items: List[Dict[str, Any]]
    include_uncertainty: bool = False


class PredictResponse(BaseModel):
    status: str
    predictions: Dict[str, Any]


# ============ Endpoints ============

@router.get("/best-model")
async def get_best_model(db: AsyncSession = Depends(get_db)):
    """Récupère le meilleur modèle entraîné."""
    result = await db.execute(
        text("""
            SELECT model_id, model_type, accuracy, precision_score, recall, f1_score, roc_auc, pr_auc, created_at
            FROM models 
            WHERE is_active = TRUE 
            ORDER BY roc_auc DESC NULLS LAST, f1_score DESC NULLS LAST
            LIMIT 1
        """)
    )
    row = result.fetchone()
    
    if not row:
        # Essayer de récupérer depuis le service ML
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{settings.ML_SERVICE_URL}/api/models/best")
                if response.status_code == 200:
                    return {"status": "success", "model": response.json()}
        except Exception as e:
            logger.warning(f"Could not fetch from ML service: {e}")
        
        raise HTTPException(status_code=404, detail="No trained model found")
    
    return {
        "status": "success",
        "model": {
            "model_id": row[0],
            "model_type": row[1],
            "accuracy": row[2],
            "accuracy_percent": (row[2] or 0) * 100,
            "metrics": {
                "accuracy": row[2],
                "precision": row[3],
                "recall": row[4],
                "f1": row[5],
                "roc_auc": row[6],
                "pr_auc": row[7]
            },
            "created_at": row[8].isoformat() if row[8] else None
        }
    }


@router.post("/predict")
async def predict(request: PredictRequest, db: AsyncSession = Depends(get_db)):
    """Fait des prédictions avec le meilleur modèle."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.ML_SERVICE_URL}/predict",
                json={
                    "items": request.items,
                    "include_uncertainty": request.include_uncertainty
                }
            )
            
            if response.status_code == 200:
                return {"status": "success", "predictions": response.json()}
            else:
                raise HTTPException(status_code=response.status_code, detail="ML service error")
                
    except httpx.RequestError as e:
        logger.error(f"ML service request failed: {e}")
        raise HTTPException(status_code=503, detail="ML service unavailable")


@router.get("/models")
async def list_models(db: AsyncSession = Depends(get_db)):
    """Liste tous les modèles entraînés."""
    result = await db.execute(
        text("""
            SELECT model_id, model_type, accuracy, precision_score, recall, f1_score, roc_auc, pr_auc, 
                   dataset_id, repo_id, created_at, is_active
            FROM models 
            ORDER BY created_at DESC
        """)
    )
    rows = result.fetchall()
    
    models = []
    for row in rows:
        models.append({
            "model_id": row[0],
            "model_type": row[1],
            "metrics": {
                "accuracy": row[2],
                "precision": row[3],
                "recall": row[4],
                "f1_score": row[5],
                "roc_auc": row[6],
                "pr_auc": row[7]
            },
            "dataset_id": row[8],
            "repo_id": row[9],
            "created_at": row[10].isoformat() if row[10] else None,
            "is_active": row[11]
        })
    
    return {"status": "success", "models": models}


@router.post("/trigger-pipeline/{repo_id}")
async def trigger_ml_pipeline(repo_id: int, db: AsyncSession = Depends(get_db)):
    """
    Déclenche le pipeline ML complet:
    1. Prétraitement et génération de features
    2. Entraînement du modèle
    3. Prédictions
    4. Priorisation
    """
    # Vérifier que le repo existe
    result = await db.execute(
        text("SELECT id, name FROM repositories WHERE id = :id"),
        {"id": repo_id}
    )
    if not result.fetchone():
        raise HTTPException(status_code=404, detail="Repository not found")
    
    pipeline_results = {
        "repo_id": repo_id,
        "steps": []
    }
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Étape 1: Générer les features
            logger.info(f"Step 1: Generating features for repo {repo_id}")
            features_response = await client.post(
                f"{settings.PRETRAITEMENT_URL}/features/generate",
                json={"repo_id": repo_id, "balancing_strategy": "smote"}
            )
            
            if features_response.status_code == 200:
                features_data = features_response.json()
                pipeline_results["steps"].append({
                    "step": "features",
                    "status": "success",
                    "data": features_data
                })
                dataset_id = features_data.get("dataset_id")
            else:
                raise HTTPException(status_code=500, detail="Feature generation failed")
            
            # Étape 2: Entraîner le modèle
            logger.info(f"Step 2: Training model for dataset {dataset_id}")
            train_response = await client.post(
                f"{settings.ML_SERVICE_URL}/train/auto",
                json={
                    "dataset_id": dataset_id,
                    "repo_id": repo_id,
                    "model_family": "ensemble",
                    "target_metric": "roc_auc"
                }
            )
            
            if train_response.status_code == 200:
                train_data = train_response.json()
                pipeline_results["steps"].append({
                    "step": "training",
                    "status": "success",
                    "data": train_data
                })
                model_id = train_data.get("model_id")
            else:
                raise HTTPException(status_code=500, detail="Model training failed")
            
            # Étape 3: Faire des prédictions
            logger.info(f"Step 3: Making predictions with model {model_id}")
            predict_response = await client.post(
                f"{settings.ML_SERVICE_URL}/predict",
                json={"dataset_id": dataset_id, "model_id": model_id}
            )
            
            if predict_response.status_code == 200:
                predict_data = predict_response.json()
                pipeline_results["steps"].append({
                    "step": "prediction",
                    "status": "success",
                    "data": predict_data
                })
            
            # Étape 4: Priorisation
            logger.info(f"Step 4: Prioritizing tests")
            if predict_response.status_code == 200:
                predictions = predict_data.get("predictions", [])
                items = [
                    {
                        "id": p.get("id", f"item_{i}"),
                        "risk": p.get("probability", p.get("risk_score", 0.5)),
                        "effort": 100,
                        "criticite": 1.0
                    }
                    for i, p in enumerate(predictions[:50])  # Limiter à 50 items
                ]
                
                if items:
                    prior_response = await client.post(
                        f"{settings.PRIORISATION_URL}/prioritize",
                        json={
                            "repo_id": repo_id,
                            "items": items,
                            "budget": 1000,
                            "weights": {"risk": 1.0, "crit": 0.5}
                        }
                    )
                    
                    if prior_response.status_code == 200:
                        pipeline_results["steps"].append({
                            "step": "prioritization",
                            "status": "success",
                            "data": prior_response.json()
                        })
    
    except httpx.RequestError as e:
        logger.error(f"Pipeline failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")
    
    pipeline_results["status"] = "completed"
    return pipeline_results
