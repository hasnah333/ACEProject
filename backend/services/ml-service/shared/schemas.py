"""
Pydantic schemas for ML Service API.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ============= Schema Endpoint =============
class ColumnInfo(BaseModel):
    """Information about a single column."""
    name: str
    dtype: str
    missing_count: int
    missing_percent: float
    unique_count: int
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    std_value: Optional[float] = None


class SchemaResponse(BaseModel):
    """Response from /schema endpoint."""
    total_rows: int
    total_columns: int
    columns: List[ColumnInfo]
    features_used: List[str]
    features_ignored: List[str]
    target_column: str
    target_distribution: Dict[str, int]


# ============= Build Dataset Endpoint =============
class BuildDatasetRequest(BaseModel):
    """Request for /build-dataset endpoint."""
    data_path: Optional[str] = None
    train_ratio: float = Field(default=0.70, ge=0.0, le=1.0)
    val_ratio: float = Field(default=0.15, ge=0.0, le=1.0)
    test_ratio: float = Field(default=0.15, ge=0.0, le=1.0)


class SplitInfo(BaseModel):
    """Information about a data split."""
    n_samples: int
    n_positive: int
    positive_rate: float
    date_min: str
    date_max: str


class BuildDatasetResponse(BaseModel):
    """Response from /build-dataset endpoint."""
    success: bool
    message: str
    train_info: SplitInfo
    val_info: SplitInfo
    test_info: SplitInfo
    feature_count: int
    pipeline_path: str
    manifest_path: str


# ============= Transform Endpoint =============
class TransformRequest(BaseModel):
    """Request for /transform endpoint."""
    records: List[Dict[str, Any]]


class TransformResponse(BaseModel):
    """Response from /transform endpoint."""
    success: bool
    transformed_records: List[Dict[str, float]]
    feature_names: List[str]


# ============= Train Endpoint =============
class TrainRequest(BaseModel):
    """Request for /train endpoint."""
    models: List[str] = Field(default=["logistic", "random_forest", "hist_gradient"])
    calibrate_best: bool = True


class ModelMetrics(BaseModel):
    """Metrics for a single model."""
    model_name: str
    auc_roc: float
    auc_pr: float
    brier_score: float
    precision_at_50: float
    precision_at_100: float
    recall_at_50: float
    recall_at_100: float
    popt_20: float


class TrainResponse(BaseModel):
    """Response from /train endpoint."""
    success: bool
    message: str
    models_trained: List[str]
    best_model: str
    metrics: List[ModelMetrics]
    artifacts_saved: List[str]


# ============= Score Endpoint =============
class ClassScore(BaseModel):
    """Risk score for a single class."""
    class_fqn: str
    repo: str
    module: str
    loc: int
    risk_score: float


class ScoreRequest(BaseModel):
    """Request for /score endpoint."""
    records: Optional[List[Dict[str, Any]]] = None
    use_test_set: bool = False


class ScoreResponse(BaseModel):
    """Response from /score endpoint."""
    success: bool
    scores: List[ClassScore]


# ============= Recommend Endpoint =============
class RecommendRequest(BaseModel):
    """Request for /recommend endpoint."""
    top_k: Optional[int] = Field(default=20, ge=1)
    budget_loc: Optional[int] = None
    alpha: float = Field(default=0.1, ge=0.0)
    use_test_set: bool = True


class Recommendation(BaseModel):
    """A single recommendation."""
    rank: int
    class_fqn: str
    repo: str
    module: str
    loc: int
    risk_score: float
    effort_score: float
    cumulative_loc: int


class RecommendResponse(BaseModel):
    """Response from /recommend endpoint."""
    success: bool
    recommendations: List[Recommendation]
    total_loc: int
    expected_defects: float


# ============= Health Endpoint =============
class HealthResponse(BaseModel):
    """Response from /health endpoint."""
    status: str
    service: str
    models_loaded: bool
    pipeline_loaded: bool
