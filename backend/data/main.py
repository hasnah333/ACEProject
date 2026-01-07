"""
ML Service - FastAPI Application
================================
Port: 8003

This service exposes the trained ML model for defect prediction.
Endpoints:
    - /health - Health check
    - /predict - Predict defect probability for code
    - /predict/batch - Batch predictions
    - /model/info - Model information
    - /train/auto - Trigger training pipeline
"""

import os
import json
import pickle
import logging
import pandas as pd
import numpy as np
import re
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============ Configuration ============

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://ace_user:ace_password@postgres:5432/ace_db"
    REDIS_URL: str = "redis://redis:6379"
    MLFLOW_TRACKING_URI: str = "http://mlflow:5000"
    MODELS_PATH: str = "/app/models"
    DATASETS_PATH: str = "/app/datasets"
    ARTIFACTS_PATH: str = "/app/artifacts"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# ============ ML Model Loading ============

MODEL_DATA = None


def load_model():
    """Load the trained model from disk."""
    global MODEL_DATA
    
    model_path = os.path.join(settings.MODELS_PATH, 'best_model.pkl')
    
    if not os.path.exists(model_path):
        # Try local path
        local_path = os.path.join(os.path.dirname(__file__), 'final_model', 'best_model.pkl')
        if os.path.exists(local_path):
            model_path = local_path
        else:
            logger.warning(f"Model not found at {model_path} or {local_path}")
            return None
    
    try:
        with open(model_path, 'rb') as f:
            MODEL_DATA = pickle.load(f)
        logger.info(f"Model loaded successfully from {model_path}")
        return MODEL_DATA
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return None


def get_model_info() -> Dict[str, Any]:
    """Get information about the loaded model."""
    results_path = os.path.join(settings.MODELS_PATH, 'results.json')
    
    if not os.path.exists(results_path):
        local_path = os.path.join(os.path.dirname(__file__), 'final_model', 'results.json')
        if os.path.exists(local_path):
            results_path = local_path
    
    if os.path.exists(results_path):
        with open(results_path, 'r') as f:
            return json.load(f)
    
    return {
        "accuracy": 0.0,
        "f1": 0.0,
        "recall": 0.0,
        "precision": 0.0,
        "auc": 0.0,
        "threshold": 0.5,
        "best_model": "Unknown",
        "best_smote": "Unknown"
    }


# ============ Feature Extraction ============

def extract_features_from_code(code: str) -> Dict[str, float]:
    """Extract features from source code for prediction."""
    lines = code.split('\n')
    features = {}
    
    # Size metrics
    features['loc'] = len(lines)
    features['sloc'] = len([l for l in lines if l.strip() and not l.strip().startswith('//')])
    features['blank_lines'] = len([l for l in lines if not l.strip()])
    features['comment_lines'] = len([l for l in lines if '//' in l or '/*' in l or l.strip().startswith('*')])
    
    # Complexity metrics
    features['if_count'] = len(re.findall(r'\bif\s*\(', code))
    features['else_count'] = len(re.findall(r'\belse\b', code))
    features['for_count'] = len(re.findall(r'\bfor\s*\(', code))
    features['while_count'] = len(re.findall(r'\bwhile\s*\(', code))
    features['switch_count'] = len(re.findall(r'\bswitch\s*\(', code))
    features['case_count'] = len(re.findall(r'\bcase\s+', code))
    features['try_count'] = len(re.findall(r'\btry\s*{', code))
    features['catch_count'] = len(re.findall(r'\bcatch\s*\(', code))
    
    # Cyclomatic complexity
    and_or = len(re.findall(r'&&|\|\|', code))
    ternary = len(re.findall(r'\?[^:]+:', code))
    features['cyclomatic'] = 1 + features['if_count'] + features['for_count'] + \
                              features['while_count'] + and_or + ternary
    
    # Structure metrics
    features['method_count'] = max(1, len(re.findall(
        r'(public|private|protected)\s+[\w<>\[\]]+\s+\w+\s*\([^)]*\)\s*[{;]', code)))
    features['class_count'] = len(re.findall(r'\bclass\s+\w+', code))
    features['interface_count'] = len(re.findall(r'\binterface\s+\w+', code))
    features['import_count'] = len(re.findall(r'\bimport\s+', code))
    features['return_count'] = len(re.findall(r'\breturn\b', code))
    features['new_count'] = len(re.findall(r'\bnew\s+\w+', code))
    
    # Risk indicators
    features['throw_count'] = len(re.findall(r'\bthrow\s+', code))
    features['null_check'] = len(re.findall(r'==\s*null|!=\s*null', code))
    features['instanceof_count'] = len(re.findall(r'\binstanceof\b', code))
    features['synchronized_count'] = len(re.findall(r'\bsynchronized\b', code))
    features['static_count'] = len(re.findall(r'\bstatic\b', code))
    features['final_count'] = len(re.findall(r'\bfinal\b', code))
    features['assert_count'] = len(re.findall(r'\bassert\b', code))
    
    # Derived metrics
    features['nesting_depth'] = features['if_count'] + features['for_count'] + features['while_count']
    features['complexity_per_method'] = features['cyclomatic'] / features['method_count']
    features['loc_per_method'] = features['sloc'] / features['method_count']
    features['comment_ratio'] = features['comment_lines'] / max(features['loc'], 1)
    features['blank_ratio'] = features['blank_lines'] / max(features['loc'], 1)
    
    # Binary indicators
    features['has_exception'] = 1 if features['try_count'] > 0 else 0
    features['has_sync'] = 1 if features['synchronized_count'] > 0 else 0
    features['high_complexity'] = 1 if features['cyclomatic'] > 10 else 0
    features['very_high_complexity'] = 1 if features['cyclomatic'] > 20 else 0
    features['long_file'] = 1 if features['loc'] > 300 else 0
    features['very_long_file'] = 1 if features['loc'] > 500 else 0
    features['many_methods'] = 1 if features['method_count'] > 10 else 0
    
    # Coupling metrics
    features['coupling'] = features['import_count'] + features['new_count']
    
    # Interaction features
    features['loc_x_complexity'] = features['loc'] * features['cyclomatic']
    features['methods_x_complexity'] = features['method_count'] * features['cyclomatic']
    features['risk_score'] = (features['has_exception'] + features['high_complexity'] + 
                              features['long_file'] + features['many_methods'])
    features['quality_score'] = features['comment_ratio'] * 10 - features['complexity_per_method']
    
    return features


# ============ Lifecycle ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - load model on startup."""
    logger.info("Starting ML Service...")
    load_model()
    yield
    logger.info("Shutting down ML Service...")


# ============ FastAPI App ============

app = FastAPI(
    title="ACE - ML Service",
    description="Machine Learning service for software defect prediction",
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

class PredictRequest(BaseModel):
    code: str = Field(..., description="Source code to analyze")
    filepath: Optional[str] = Field(None, description="Optional file path for context")
    

class PredictResponse(BaseModel):
    risk_score: float = Field(..., description="Defect probability [0-1]")
    is_buggy: bool = Field(..., description="Predicted as buggy")
    confidence: float = Field(..., description="Prediction confidence")
    features: Dict[str, float] = Field(..., description="Extracted features")


class BatchPredictRequest(BaseModel):
    items: List[Dict[str, str]] = Field(..., description="List of {code, filepath} items")


class BatchPredictResponse(BaseModel):
    predictions: List[PredictResponse]
    summary: Dict[str, Any]


class TrainRequest(BaseModel):
    dataset_id: Optional[int] = None
    use_smote: bool = True
    smote_variant: str = "BorderlineSMOTE"


class TrainResponse(BaseModel):
    status: str
    model_id: str
    metrics: Dict[str, float]


class ModelInfoResponse(BaseModel):
    model_type: str
    accuracy: float
    f1: float
    recall: float
    precision: float
    auc: float
    threshold: float
    smote_variant: str
    is_loaded: bool


# ============ Endpoints ============

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "ml-service",
        "version": "1.0.0",
        "status": "running",
        "model_loaded": MODEL_DATA is not None,
        "endpoints": {
            "health": "/health",
            "predict": "/predict",
            "predict_batch": "/predict/batch",
            "model_info": "/model/info",
            "train": "/train/auto"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_loaded": MODEL_DATA is not None,
        "version": "1.0.0"
    }


@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """Predict defect probability for a single code snippet."""
    
    if MODEL_DATA is None:
        # Return heuristic-based prediction if model not loaded
        features = extract_features_from_code(request.code)
        risk_score = min(1.0, (
            features['cyclomatic'] / 50 +
            features['loc'] / 1000 +
            features['high_complexity'] * 0.3 +
            features['long_file'] * 0.2
        ))
        return PredictResponse(
            risk_score=risk_score,
            is_buggy=risk_score > 0.5,
            confidence=0.5,  # Low confidence without model
            features=features
        )
    
    try:
        # Extract features
        features = extract_features_from_code(request.code)
        
        # Create dataframe
        feature_df = pd.DataFrame([features])
        
        # Apply scaling
        scaler = MODEL_DATA.get('scaler')
        selector = MODEL_DATA.get('selector')
        model = MODEL_DATA.get('model')
        threshold = MODEL_DATA.get('threshold', 0.5)
        
        # Transform features
        X_scaled = scaler.transform(feature_df)
        X_selected = selector.transform(X_scaled)
        
        # Predict
        proba = model.predict_proba(X_selected)[0, 1]
        is_buggy = proba >= threshold
        
        return PredictResponse(
            risk_score=float(proba),
            is_buggy=bool(is_buggy),
            confidence=abs(proba - 0.5) * 2,  # Higher when far from threshold
            features=features
        )
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict/batch", response_model=BatchPredictResponse)
async def predict_batch(request: BatchPredictRequest):
    """Batch predictions for multiple code snippets."""
    
    predictions = []
    buggy_count = 0
    total_risk = 0
    
    for item in request.items:
        code = item.get('code', '')
        filepath = item.get('filepath', '')
        
        pred_request = PredictRequest(code=code, filepath=filepath)
        pred = await predict(pred_request)
        predictions.append(pred)
        
        if pred.is_buggy:
            buggy_count += 1
        total_risk += pred.risk_score
    
    return BatchPredictResponse(
        predictions=predictions,
        summary={
            "total_items": len(predictions),
            "buggy_items": buggy_count,
            "buggy_rate": buggy_count / len(predictions) if predictions else 0,
            "avg_risk_score": total_risk / len(predictions) if predictions else 0
        }
    )


@app.get("/model/info", response_model=ModelInfoResponse)
async def model_info():
    """Get information about the loaded model."""
    info = get_model_info()
    
    return ModelInfoResponse(
        model_type=info.get('best_model', 'Unknown'),
        accuracy=info.get('accuracy', 0.0),
        f1=info.get('f1', 0.0),
        recall=info.get('recall', 0.0),
        precision=info.get('precision', 0.0),
        auc=info.get('auc', 0.0),
        threshold=info.get('threshold', 0.5),
        smote_variant=info.get('best_smote', 'Unknown'),
        is_loaded=MODEL_DATA is not None
    )


@app.post("/train/auto", response_model=TrainResponse)
async def train_auto(request: TrainRequest, background_tasks: BackgroundTasks):
    """Trigger automatic model training."""
    
    # For now, return current model info
    # In production, this would trigger the training pipeline
    info = get_model_info()
    
    return TrainResponse(
        status="completed",
        model_id="ensemble_v1",
        metrics={
            "accuracy": info.get('accuracy', 0.0),
            "f1": info.get('f1', 0.0),
            "recall": info.get('recall', 0.0),
            "precision": info.get('precision', 0.0),
            "auc": info.get('auc', 0.0)
        }
    )


@app.get("/models/list")
async def list_models():
    """List available models."""
    models_dir = settings.MODELS_PATH
    local_dir = os.path.join(os.path.dirname(__file__), 'final_model')
    
    models = []
    
    for models_path in [models_dir, local_dir]:
        if os.path.exists(models_path):
            for f in os.listdir(models_path):
                if f.endswith('.pkl'):
                    models.append({
                        "name": f.replace('.pkl', ''),
                        "path": os.path.join(models_path, f),
                        "type": "pickle"
                    })
    
    return {"models": models}


@app.get("/features/schema")
async def get_feature_schema():
    """Get the schema of features used for prediction."""
    return {
        "code_metrics": [
            "loc", "sloc", "blank_lines", "comment_lines",
            "if_count", "else_count", "for_count", "while_count",
            "switch_count", "case_count", "try_count", "catch_count",
            "cyclomatic", "method_count", "class_count", "interface_count",
            "import_count", "return_count", "new_count"
        ],
        "risk_indicators": [
            "throw_count", "null_check", "instanceof_count",
            "synchronized_count", "static_count", "final_count", "assert_count"
        ],
        "derived_metrics": [
            "nesting_depth", "complexity_per_method", "loc_per_method",
            "comment_ratio", "blank_ratio", "coupling"
        ],
        "binary_indicators": [
            "has_exception", "has_sync", "high_complexity",
            "very_high_complexity", "long_file", "very_long_file", "many_methods"
        ],
        "interaction_features": [
            "loc_x_complexity", "methods_x_complexity",
            "risk_score", "quality_score"
        ]
    }


@app.post("/reload")
async def reload_model():
    """Reload the model from disk."""
    result = load_model()
    if result:
        return {"status": "success", "message": "Model reloaded successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to reload model")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
