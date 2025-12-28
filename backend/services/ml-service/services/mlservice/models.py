"""
ML Model training and inference for defect prediction.
Enhanced with XGBoost, LightGBM, Stacking, and SMOTE.
"""
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import (
    RandomForestClassifier, 
    HistGradientBoostingClassifier,
    StackingClassifier,
    VotingClassifier
)
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import cross_val_score

# Advanced models
try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    from lightgbm import LGBMClassifier
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

# SMOTE for class imbalance
try:
    from imblearn.over_sampling import SMOTE
    from imblearn.pipeline import Pipeline as ImbPipeline
    SMOTE_AVAILABLE = True
except ImportError:
    SMOTE_AVAILABLE = False

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.config import ARTIFACTS_PATH, RANDOM_STATE, K_VALUES, POPT_EFFORT_PERCENT, MODEL_NAMES
from shared.metrics import compute_all_metrics


class ModelManager:
    """
    Enhanced model manager with XGBoost, LightGBM, Stacking, and SMOTE.
    """
    
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.calibrated_models: Dict[str, Any] = {}
        self.best_model_name: Optional[str] = None
        self.metrics: Dict[str, Dict] = {}
        self.is_trained: bool = False
        self.use_smote: bool = True
        
    def _create_model(self, model_type: str):
        """Create a model instance by type with optimized hyperparameters."""
        
        if model_type == "logistic":
            return LogisticRegression(
                class_weight="balanced",
                max_iter=2000,
                C=0.5,
                solver="lbfgs",
                random_state=RANDOM_STATE,
                n_jobs=-1
            )
        
        elif model_type == "random_forest":
            return RandomForestClassifier(
                n_estimators=300,
                class_weight="balanced_subsample",
                max_depth=20,
                min_samples_split=3,
                min_samples_leaf=2,
                max_features="sqrt",
                bootstrap=True,
                oob_score=True,
                random_state=RANDOM_STATE,
                n_jobs=-1
            )
        
        elif model_type == "hist_gradient":
            return HistGradientBoostingClassifier(
                max_iter=300,
                max_depth=12,
                learning_rate=0.05,
                min_samples_leaf=10,
                max_leaf_nodes=50,
                l2_regularization=0.1,
                early_stopping=True,
                validation_fraction=0.1,
                n_iter_no_change=20,
                random_state=RANDOM_STATE
            )
        
        elif model_type == "xgboost" and XGBOOST_AVAILABLE:
            return XGBClassifier(
                n_estimators=300,
                max_depth=10,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                scale_pos_weight=5,  # For imbalanced classes
                use_label_encoder=False,
                eval_metric='logloss',
                random_state=RANDOM_STATE,
                n_jobs=-1
            )
        
        elif model_type == "lightgbm" and LIGHTGBM_AVAILABLE:
            return LGBMClassifier(
                n_estimators=300,
                max_depth=10,
                learning_rate=0.05,
                num_leaves=50,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                class_weight="balanced",
                random_state=RANDOM_STATE,
                n_jobs=-1,
                verbose=-1
            )
        
        elif model_type == "stacking":
            # Stacking ensemble of best models
            base_estimators = [
                ('rf', RandomForestClassifier(
                    n_estimators=100, max_depth=15, class_weight="balanced",
                    random_state=RANDOM_STATE, n_jobs=-1
                )),
                ('hgb', HistGradientBoostingClassifier(
                    max_iter=100, max_depth=8, learning_rate=0.1,
                    random_state=RANDOM_STATE
                )),
            ]
            
            if XGBOOST_AVAILABLE:
                base_estimators.append(
                    ('xgb', XGBClassifier(
                        n_estimators=100, max_depth=8, learning_rate=0.1,
                        scale_pos_weight=5, random_state=RANDOM_STATE, n_jobs=-1
                    ))
                )
            
            return StackingClassifier(
                estimators=base_estimators,
                final_estimator=LogisticRegression(C=1.0, random_state=RANDOM_STATE),
                cv=3,
                stack_method='predict_proba',
                n_jobs=-1
            )
        
        elif model_type == "voting":
            # Voting ensemble
            estimators = [
                ('rf', RandomForestClassifier(
                    n_estimators=200, max_depth=15, class_weight="balanced",
                    random_state=RANDOM_STATE, n_jobs=-1
                )),
                ('hgb', HistGradientBoostingClassifier(
                    max_iter=200, max_depth=10, learning_rate=0.05,
                    random_state=RANDOM_STATE
                )),
            ]
            
            if XGBOOST_AVAILABLE:
                estimators.append(
                    ('xgb', XGBClassifier(
                        n_estimators=200, max_depth=10, learning_rate=0.05,
                        scale_pos_weight=5, random_state=RANDOM_STATE, n_jobs=-1
                    ))
                )
            
            return VotingClassifier(
                estimators=estimators,
                voting='soft',
                n_jobs=-1
            )
        
        else:
            raise ValueError(f"Unknown or unavailable model type: {model_type}")
    
    def _apply_smote(self, X: np.ndarray, y: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Apply SMOTE for class imbalance."""
        if not SMOTE_AVAILABLE or not self.use_smote:
            return X, y
        
        # Only apply if imbalance is significant
        pos_rate = y.mean()
        if pos_rate > 0.3:  # Not too imbalanced
            return X, y
        
        try:
            smote = SMOTE(
                sampling_strategy=0.5,  # Target 50% minority
                random_state=RANDOM_STATE,
                k_neighbors=5
            )
            X_resampled, y_resampled = smote.fit_resample(X, y)
            print(f"   SMOTE: {len(y)} -> {len(y_resampled)} samples (pos: {y.mean():.2%} -> {y_resampled.mean():.2%})")
            return X_resampled, y_resampled
        except Exception as e:
            print(f"   SMOTE failed: {e}")
            return X, y
    
    def get_available_models(self) -> List[str]:
        """Get list of available model types."""
        models = ["logistic", "random_forest", "hist_gradient", "stacking", "voting"]
        
        if XGBOOST_AVAILABLE:
            models.append("xgboost")
        if LIGHTGBM_AVAILABLE:
            models.append("lightgbm")
        
        return models
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        effort_val: np.ndarray,
        model_types: List[str] = None,
        calibrate_best: bool = True,
        use_smote: bool = True
    ) -> Dict[str, Any]:
        """
        Train all specified models and evaluate on validation set.
        """
        self.use_smote = use_smote
        
        if model_types is None:
            # Default: include advanced models if available
            model_types = ["logistic", "random_forest", "hist_gradient"]
            if XGBOOST_AVAILABLE:
                model_types.append("xgboost")
            if LIGHTGBM_AVAILABLE:
                model_types.append("lightgbm")
        
        # Apply SMOTE to training data
        X_train_balanced, y_train_balanced = self._apply_smote(X_train, y_train)
        
        results = {
            "models_trained": [],
            "metrics": [],
            "best_model": None,
            "best_auc_roc": 0.0
        }
        
        for model_type in model_types:
            try:
                model_name = MODEL_NAMES.get(model_type, model_type)
                print(f"Training {model_name}...")
                
                # Create and train model
                model = self._create_model(model_type)
                model.fit(X_train_balanced, y_train_balanced)
                self.models[model_type] = model
                
                # Predict probabilities on validation set
                y_scores = model.predict_proba(X_val)[:, 1]
                
                # Compute metrics
                metrics = compute_all_metrics(
                    y_true=y_val,
                    y_scores=y_scores,
                    effort=effort_val,
                    k_values=K_VALUES,
                    popt_percent=POPT_EFFORT_PERCENT
                )
                
                self.metrics[model_type] = metrics
                
                # Format metrics for response
                model_metrics = {
                    "model_name": model_name,
                    "auc_roc": round(metrics["auc_roc"], 4),
                    "auc_pr": round(metrics["auc_pr"], 4),
                    "brier_score": round(metrics["brier_score"], 4),
                    "precision_at_50": round(metrics.get("precision_at_50", 0), 4),
                    "precision_at_100": round(metrics.get("precision_at_100", 0), 4),
                    "recall_at_50": round(metrics.get("recall_at_50", 0), 4),
                    "recall_at_100": round(metrics.get("recall_at_100", 0), 4),
                    "popt_20": round(metrics.get("popt_20", 0), 4)
                }
                
                results["metrics"].append(model_metrics)
                results["models_trained"].append(model_name)
                
                print(f"   AUC-ROC: {metrics['auc_roc']:.4f}, Precision@50: {metrics.get('precision_at_50', 0):.4f}")
                
                # Track best model
                if metrics["auc_roc"] > results["best_auc_roc"]:
                    results["best_auc_roc"] = metrics["auc_roc"]
                    results["best_model"] = model_type
                    self.best_model_name = model_type
                    
            except Exception as e:
                print(f"   Failed to train {model_type}: {e}")
                continue
        
        # Calibrate best model
        if calibrate_best and self.best_model_name:
            try:
                print(f"Calibrating best model ({MODEL_NAMES.get(self.best_model_name, self.best_model_name)})...")
                best_model = self.models[self.best_model_name]
                
                calibrated = CalibratedClassifierCV(best_model, method="sigmoid", cv="prefit")
                calibrated.fit(X_val, y_val)
                self.calibrated_models[self.best_model_name] = calibrated
            except Exception as e:
                print(f"   Calibration failed: {e}")
        
        self.is_trained = True
        
        return results
    
    def predict(
        self,
        X: np.ndarray,
        model_type: str = None,
        use_calibrated: bool = True
    ) -> np.ndarray:
        """Predict risk scores using trained model."""
        if not self.is_trained:
            raise ValueError("No models trained. Call train() first.")
        
        if model_type is None:
            model_type = self.best_model_name
        
        if model_type not in self.models:
            raise ValueError(f"Model not found: {model_type}")
        
        if use_calibrated and model_type in self.calibrated_models:
            model = self.calibrated_models[model_type]
        else:
            model = self.models[model_type]
        
        return model.predict_proba(X)[:, 1]
    
    def get_feature_importance(
        self,
        feature_names: List[str],
        model_type: str = None,
        top_k: int = 15
    ) -> List[Dict[str, Any]]:
        """Get feature importance from the model."""
        if model_type is None:
            model_type = self.best_model_name
        
        model = self.models.get(model_type)
        if model is None:
            return []
        
        importances = None
        
        # Get importance based on model type
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
        elif hasattr(model, "coef_"):
            importances = np.abs(model.coef_[0])
        
        if importances is None:
            return []
        
        # Handle dimension mismatch
        if len(importances) != len(feature_names):
            return []
        
        # Sort by importance
        indices = np.argsort(importances)[::-1][:top_k]
        
        result = []
        for i, idx in enumerate(indices):
            if idx < len(feature_names):
                result.append({
                    "rank": i + 1,
                    "feature": feature_names[idx],
                    "importance": float(importances[idx])
                })
        
        return result
    
    def save(self, path: str = None) -> List[str]:
        """Save all trained models to disk."""
        if path is None:
            path = ARTIFACTS_PATH
        
        artifacts_dir = Path(path)
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = []
        
        # Save all models
        for model_type, model in self.models.items():
            model_path = artifacts_dir / f"model_{model_type}.pkl"
            joblib.dump(model, model_path)
            saved_files.append(str(model_path))
        
        # Save calibrated models
        for model_type, model in self.calibrated_models.items():
            model_path = artifacts_dir / f"model_{model_type}_calibrated.pkl"
            joblib.dump(model, model_path)
            saved_files.append(str(model_path))
        
        # Save metadata
        metadata = {
            "best_model_name": self.best_model_name,
            "metrics": self.metrics,
            "is_trained": self.is_trained
        }
        metadata_path = artifacts_dir / "models_metadata.pkl"
        joblib.dump(metadata, metadata_path)
        saved_files.append(str(metadata_path))
        
        return saved_files
    
    def load(self, path: str = None) -> None:
        """Load models from disk."""
        if path is None:
            path = ARTIFACTS_PATH
        
        artifacts_dir = Path(path)
        
        # Load metadata
        metadata_path = artifacts_dir / "models_metadata.pkl"
        if metadata_path.exists():
            metadata = joblib.load(metadata_path)
            self.best_model_name = metadata.get("best_model_name")
            self.metrics = metadata.get("metrics", {})
            self.is_trained = metadata.get("is_trained", False)
        
        # Load models
        all_model_types = self.get_available_models()
        for model_type in all_model_types:
            model_path = artifacts_dir / f"model_{model_type}.pkl"
            if model_path.exists():
                try:
                    self.models[model_type] = joblib.load(model_path)
                except Exception:
                    pass
            
            calibrated_path = artifacts_dir / f"model_{model_type}_calibrated.pkl"
            if calibrated_path.exists():
                try:
                    self.calibrated_models[model_type] = joblib.load(calibrated_path)
                except Exception:
                    pass


def load_training_data() -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Load preprocessed training data from artifacts."""
    artifacts_dir = Path(ARTIFACTS_PATH)
    
    X_train = np.load(artifacts_dir / "X_train.npy")
    y_train = np.load(artifacts_dir / "y_train.npy")
    X_val = np.load(artifacts_dir / "X_val.npy")
    y_val = np.load(artifacts_dir / "y_val.npy")
    
    effort_val = np.ones(len(y_val)) * 100
    
    return X_train, y_train, X_val, y_val, effort_val


def load_test_data() -> Tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """Load preprocessed test data with metadata."""
    artifacts_dir = Path(ARTIFACTS_PATH)
    
    X_test = np.load(artifacts_dir / "X_test.npy")
    y_test = np.load(artifacts_dir / "y_test.npy")
    
    test_meta = pd.read_csv(artifacts_dir / "test_metadata.csv")
    
    return X_test, y_test, test_meta
