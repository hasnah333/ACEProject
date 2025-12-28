"""
FastAPI application for Preprocessing Service.
"""
import pandas as pd
from fastapi import FastAPI, HTTPException
from pathlib import Path
from typing import List, Dict, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.config import MAIN_DATASET, ARTIFACTS_PATH
from shared.schemas import (
    SchemaResponse, ColumnInfo,
    BuildDatasetRequest, BuildDatasetResponse, SplitInfo,
    TransformRequest, TransformResponse
)
from services.preprocessing.pipeline import PreprocessingPipeline, build_dataset

app = FastAPI(
    title="Preprocessing Service",
    description="Data preprocessing and feature engineering for ML defect prediction",
    version="1.0.0"
)

# Global pipeline instance
_pipeline: PreprocessingPipeline = None


def get_pipeline() -> PreprocessingPipeline:
    """Get or load the preprocessing pipeline."""
    global _pipeline
    if _pipeline is None:
        _pipeline = PreprocessingPipeline()
        pipeline_path = Path(ARTIFACTS_PATH) / "preprocess_pipeline.pkl"
        if pipeline_path.exists():
            _pipeline.load(str(pipeline_path))
    return _pipeline


@app.get("/")
async def root():
    """Service root endpoint."""
    return {
        "service": "Preprocessing Service",
        "version": "1.0.0",
        "endpoints": ["/schema", "/build-dataset", "/transform"]
    }


@app.post("/schema", response_model=SchemaResponse)
async def get_schema(data_path: str = None):
    """
    Analyze dataset schema and return column information.
    
    Returns:
        - Column names, types, missing percentages
        - Features used vs ignored
        - Target distribution
    """
    if data_path is None:
        data_path = MAIN_DATASET
    
    if not Path(data_path).exists():
        raise HTTPException(status_code=404, detail=f"Data file not found: {data_path}")
    
    try:
        pipeline = PreprocessingPipeline()
        df = pd.read_csv(data_path)
        schema_info = pipeline.analyze_schema(df)
        
        return SchemaResponse(
            total_rows=schema_info["total_rows"],
            total_columns=schema_info["total_columns"],
            columns=[ColumnInfo(**col) for col in schema_info["columns"]],
            features_used=schema_info["features_used"],
            features_ignored=schema_info["features_ignored"],
            target_column=schema_info["target_column"],
            target_distribution=schema_info["target_distribution"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/build-dataset", response_model=BuildDatasetResponse)
async def build_dataset_endpoint(request: BuildDatasetRequest = None):
    """
    Build preprocessed dataset with time-aware split.
    
    Performs:
    - Load and clean data
    - Time-aware split (70% train / 15% val / 15% test)
    - Feature engineering and transformation
    - Save artifacts (pipeline, data, manifest)
    """
    global _pipeline
    
    if request is None:
        request = BuildDatasetRequest()
    
    data_path = request.data_path or MAIN_DATASET
    
    if not Path(data_path).exists():
        raise HTTPException(status_code=404, detail=f"Data file not found: {data_path}")
    
    try:
        result = build_dataset(
            data_path=data_path,
            train_ratio=request.train_ratio,
            val_ratio=request.val_ratio,
            test_ratio=request.test_ratio
        )
        
        # Reload pipeline
        _pipeline = PreprocessingPipeline()
        _pipeline.load()
        
        return BuildDatasetResponse(
            success=result["success"],
            message=result["message"],
            train_info=SplitInfo(**result["train_info"]),
            val_info=SplitInfo(**result["val_info"]),
            test_info=SplitInfo(**result["test_info"]),
            feature_count=result["feature_count"],
            pipeline_path=result["pipeline_path"],
            manifest_path=result["manifest_path"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/transform", response_model=TransformResponse)
async def transform_data(request: TransformRequest):
    """
    Transform new records using the fitted pipeline.
    
    Input: List of records as dictionaries
    Output: Transformed feature vectors
    """
    pipeline = get_pipeline()
    
    if not pipeline.is_fitted:
        raise HTTPException(
            status_code=400, 
            detail="Pipeline not fitted. Call /build-dataset first."
        )
    
    try:
        df = pd.DataFrame(request.records)
        X = pipeline.transform(df)
        
        # Convert to list of dicts
        transformed_records = []
        for row in X:
            record = {name: float(val) for name, val in zip(pipeline.feature_names, row)}
            transformed_records.append(record)
        
        return TransformResponse(
            success=True,
            transformed_records=transformed_records,
            feature_names=pipeline.feature_names
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    pipeline = get_pipeline()
    return {
        "status": "healthy",
        "service": "preprocessing",
        "pipeline_loaded": pipeline.is_fitted
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
