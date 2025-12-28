"""
Enhanced preprocessing pipeline for ML Service.
Includes advanced feature engineering, outlier handling, and polynomial features.
"""
import pandas as pd
import numpy as np
import json
import joblib
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional
from sklearn.preprocessing import StandardScaler, OneHotEncoder, RobustScaler, PolynomialFeatures
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.feature_selection import SelectKBest, mutual_info_classif

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.config import (
    ID_COLUMNS, CATEGORICAL_COLUMNS, TARGET_COLUMN, LEAKAGE_COLUMNS,
    TRAIN_RATIO, VAL_RATIO, TEST_RATIO,
    COVERAGE_MIN, COVERAGE_MAX, FLAKY_MIN, FLAKY_MAX,
    ARTIFACTS_PATH, RANDOM_STATE,
    USE_PROBABILITY_TARGET, PROBABILITY_THRESHOLD, PROBABILITY_COLUMN
)


class PreprocessingPipeline:
    """
    Enhanced preprocessing pipeline with advanced feature engineering.
    """
    
    def __init__(self, use_feature_ratios: bool = True, use_robust_scaling: bool = True):
        self.pipeline: Optional[ColumnTransformer] = None
        self.feature_names: List[str] = []
        self.numeric_features: List[str] = []
        self.categorical_features: List[str] = []
        self.missing_indicators: List[str] = []
        self.engineered_features: List[str] = []
        self.is_fitted: bool = False
        self.use_feature_ratios = use_feature_ratios
        self.use_robust_scaling = use_robust_scaling
        
    def analyze_schema(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze dataset schema and return column information."""
        columns_info = []
        
        for col in df.columns:
            info = {
                "name": col,
                "dtype": str(df[col].dtype),
                "missing_count": int(df[col].isna().sum()),
                "missing_percent": round(float(df[col].isna().mean() * 100), 2),
                "unique_count": int(df[col].nunique())
            }
            
            if pd.api.types.is_numeric_dtype(df[col]):
                info["min_value"] = float(df[col].min()) if not df[col].isna().all() else None
                info["max_value"] = float(df[col].max()) if not df[col].isna().all() else None
                info["mean_value"] = float(df[col].mean()) if not df[col].isna().all() else None
                info["std_value"] = float(df[col].std()) if not df[col].isna().all() else None
            
            columns_info.append(info)
        
        all_cols = set(df.columns)
        ignore_cols = set(ID_COLUMNS + [TARGET_COLUMN, PROBABILITY_COLUMN] + LEAKAGE_COLUMNS)
        features_used = [c for c in df.columns if c not in ignore_cols and c in all_cols]
        features_ignored = [c for c in ignore_cols if c in all_cols]
        
        target_dist = {}
        if TARGET_COLUMN in df.columns:
            target_dist = df[TARGET_COLUMN].value_counts().to_dict()
            target_dist = {str(k): int(v) for k, v in target_dist.items()}
        
        return {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "columns": columns_info,
            "features_used": features_used,
            "features_ignored": features_ignored,
            "target_column": TARGET_COLUMN,
            "target_distribution": target_dist
        }
    
    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create engineered features: ratios, log transforms, interactions.
        """
        df = df.copy()
        self.engineered_features = []
        
        # 1. Complexity per LOC (normalized complexity)
        if "cyclomatic_complexity" in df.columns and "loc" in df.columns:
            df["complexity_per_loc"] = df["cyclomatic_complexity"] / (df["loc"] + 1)
            self.engineered_features.append("complexity_per_loc")
        
        # 2. Total coverage score
        coverage_cols = ["line_coverage_pct", "branch_coverage_pct", "mutation_score_pct"]
        existing_cov = [c for c in coverage_cols if c in df.columns]
        if existing_cov:
            df["total_coverage"] = df[existing_cov].mean(axis=1)
            self.engineered_features.append("total_coverage")
        
        # 3. Code smells per LOC
        if "code_smells" in df.columns and "loc" in df.columns:
            df["smells_per_loc"] = df["code_smells"] / (df["loc"] + 1)
            self.engineered_features.append("smells_per_loc")
        
        # 4. Churn intensity (changes relative to size)
        if "added_loc_30d" in df.columns and "deleted_loc_30d" in df.columns and "loc" in df.columns:
            df["churn_total"] = df["added_loc_30d"] + df["deleted_loc_30d"]
            df["churn_intensity"] = df["churn_total"] / (df["loc"] + 1)
            self.engineered_features.extend(["churn_total", "churn_intensity"])
        
        # 5. Author concentration (inverse of num_authors)
        if "num_authors_30d" in df.columns:
            df["author_concentration"] = 1 / (df["num_authors_30d"] + 1)
            self.engineered_features.append("author_concentration")
        
        # 6. Age factor (log of days since change)
        if "days_since_last_change" in df.columns:
            df["log_age"] = np.log1p(df["days_since_last_change"])
            self.engineered_features.append("log_age")
        
        # 7. Bug commit rate
        if "bugfix_commits_90d" in df.columns and "num_commits_30d" in df.columns:
            df["bugfix_rate"] = df["bugfix_commits_90d"] / (df["num_commits_30d"] * 3 + 1)
            self.engineered_features.append("bugfix_rate")
        
        # 8. Test failure rate
        if "tests_failed_30d" in df.columns:
            df["log_failed_tests"] = np.log1p(df["tests_failed_30d"])
            self.engineered_features.append("log_failed_tests")
        
        # 9. Coupling metrics combination
        coupling_cols = ["cbo", "fan_in", "fan_out", "rfc"]
        existing_coupling = [c for c in coupling_cols if c in df.columns]
        if len(existing_coupling) >= 2:
            df["coupling_score"] = df[existing_coupling].mean(axis=1)
            self.engineered_features.append("coupling_score")
        
        # 10. Inheritance depth risk
        if "dit" in df.columns and "noc" in df.columns:
            df["inheritance_risk"] = df["dit"] * (df["noc"] + 1)
            self.engineered_features.append("inheritance_risk")
        
        # 11. Log transforms for skewed features
        skewed_cols = ["loc", "wmc", "lcom"]
        for col in skewed_cols:
            if col in df.columns:
                log_col = f"log_{col}"
                df[log_col] = np.log1p(df[col])
                self.engineered_features.append(log_col)
        
        # 12. Risk composite score
        risk_components = []
        if "cyclomatic_complexity" in df.columns:
            risk_components.append(df["cyclomatic_complexity"] / df["cyclomatic_complexity"].max())
        if "code_smells" in df.columns:
            risk_components.append(df["code_smells"] / (df["code_smells"].max() + 1))
        if "bugfix_commits_90d" in df.columns:
            risk_components.append(df["bugfix_commits_90d"] / (df["bugfix_commits_90d"].max() + 1))
        
        if risk_components:
            df["risk_composite"] = sum(risk_components) / len(risk_components)
            self.engineered_features.append("risk_composite")
        
        print(f"   Engineered {len(self.engineered_features)} new features")
        
        return df
    
    def _handle_outliers(self, df: pd.DataFrame, numeric_cols: List[str]) -> pd.DataFrame:
        """Apply winsorization to handle outliers."""
        df = df.copy()
        
        for col in numeric_cols:
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                q01 = df[col].quantile(0.01)
                q99 = df[col].quantile(0.99)
                df[col] = df[col].clip(q01, q99)
        
        return df
    
    def load_and_clean(self, data_path: str) -> pd.DataFrame:
        """Load CSV and perform cleaning with feature engineering."""
        df = pd.read_csv(data_path)
        
        # Parse dates
        if "snapshot_date" in df.columns:
            df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
        
        # Clip coverage columns
        coverage_cols = ["line_coverage_pct", "branch_coverage_pct", "mutation_score_pct"]
        for col in coverage_cols:
            if col in df.columns:
                df[col] = df[col].clip(COVERAGE_MIN, COVERAGE_MAX)
        
        # Clip flaky rate
        if "flaky_rate" in df.columns:
            df["flaky_rate"] = df["flaky_rate"].clip(FLAKY_MIN, FLAKY_MAX)
        
        # Create derived target
        if USE_PROBABILITY_TARGET and PROBABILITY_COLUMN in df.columns:
            df["derived_target"] = (df[PROBABILITY_COLUMN] >= PROBABILITY_THRESHOLD).astype(int)
            print(f"Created derived_target from {PROBABILITY_COLUMN} >= {PROBABILITY_THRESHOLD}")
            print(f"  Positive rate: {df['derived_target'].mean():.2%}")
        
        # Engineer features
        if self.use_feature_ratios:
            df = self._engineer_features(df)
        
        # Remove leakage columns
        for col in LEAKAGE_COLUMNS:
            if col in df.columns:
                df = df.drop(columns=[col])
        
        return df
    
    def time_aware_split(
        self, 
        df: pd.DataFrame,
        train_ratio: float = TRAIN_RATIO,
        val_ratio: float = VAL_RATIO,
        test_ratio: float = TEST_RATIO
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Split data chronologically."""
        if "snapshot_date" not in df.columns:
            raise ValueError("snapshot_date column required")
        
        df_sorted = df.sort_values("snapshot_date").reset_index(drop=True)
        
        n = len(df_sorted)
        train_end = int(n * train_ratio)
        val_end = int(n * (train_ratio + val_ratio))
        
        return (
            df_sorted.iloc[:train_end].copy(),
            df_sorted.iloc[train_end:val_end].copy(),
            df_sorted.iloc[val_end:].copy()
        )
    
    def _identify_features(self, df: pd.DataFrame) -> None:
        """Identify numeric and categorical features."""
        all_cols = set(df.columns)
        ignore_cols = set(ID_COLUMNS + [TARGET_COLUMN, PROBABILITY_COLUMN, "derived_target"] + LEAKAGE_COLUMNS)
        
        self.categorical_features = [c for c in CATEGORICAL_COLUMNS if c in all_cols and c not in ignore_cols]
        
        self.numeric_features = []
        for col in df.columns:
            if col in ignore_cols or col in self.categorical_features:
                continue
            if pd.api.types.is_numeric_dtype(df[col]):
                self.numeric_features.append(col)
        
        print(f"   Identified {len(self.numeric_features)} numeric, {len(self.categorical_features)} categorical features")
    
    def fit(self, df: pd.DataFrame) -> None:
        """Fit the preprocessing pipeline."""
        self._identify_features(df)
        
        # Handle outliers in numeric features
        df = self._handle_outliers(df, self.numeric_features)
        
        # Missing indicators
        self.missing_indicators = []
        for col in self.numeric_features:
            if df[col].isna().any():
                self.missing_indicators.append(f"{col}_missing")
        
        # Build preprocessing pipeline
        scaler = RobustScaler() if self.use_robust_scaling else StandardScaler()
        
        numeric_transformer = Pipeline(steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", scaler)
        ])
        
        categorical_transformer = Pipeline(steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="unknown")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False))
        ])
        
        transformers = []
        if self.numeric_features:
            transformers.append(("num", numeric_transformer, self.numeric_features))
        if self.categorical_features:
            transformers.append(("cat", categorical_transformer, self.categorical_features))
        
        self.pipeline = ColumnTransformer(transformers=transformers, remainder="drop")
        self.pipeline.fit(df)
        
        # Get feature names
        self.feature_names = list(self.numeric_features)
        
        if self.categorical_features:
            cat_encoder = self.pipeline.named_transformers_["cat"].named_steps["encoder"]
            for i, cat_col in enumerate(self.categorical_features):
                for category in cat_encoder.categories_[i]:
                    self.feature_names.append(f"{cat_col}_{category}")
        
        self.feature_names.extend(self.missing_indicators)
        
        self.is_fitted = True
        print(f"   Total features after preprocessing: {len(self.feature_names)}")
    
    def transform(self, df: pd.DataFrame) -> np.ndarray:
        """Transform data using fitted pipeline."""
        if not self.is_fitted:
            raise ValueError("Pipeline not fitted.")
        
        # Handle outliers
        df = self._handle_outliers(df, self.numeric_features)
        
        X = self.pipeline.transform(df)
        
        # Add missing indicators
        if self.missing_indicators:
            missing_features = []
            for col in self.numeric_features:
                if f"{col}_missing" in self.missing_indicators:
                    missing_features.append(df[col].isna().astype(int).values.reshape(-1, 1))
            
            if missing_features:
                X = np.hstack([X, np.hstack(missing_features)])
        
        return X
    
    def fit_transform(self, df: pd.DataFrame) -> np.ndarray:
        """Fit and transform."""
        self.fit(df)
        return self.transform(df)
    
    def get_split_info(self, df: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """Get split information."""
        return {
            "n_samples": len(df),
            "n_positive": int(y.sum()),
            "positive_rate": round(float(y.mean()), 4),
            "date_min": str(df["snapshot_date"].min().date()) if "snapshot_date" in df.columns else "N/A",
            "date_max": str(df["snapshot_date"].max().date()) if "snapshot_date" in df.columns else "N/A"
        }
    
    def save(self, path: str = None) -> str:
        """Save pipeline."""
        if path is None:
            path = str(Path(ARTIFACTS_PATH) / "preprocess_pipeline.pkl")
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        state = {
            "pipeline": self.pipeline,
            "feature_names": self.feature_names,
            "numeric_features": self.numeric_features,
            "categorical_features": self.categorical_features,
            "missing_indicators": self.missing_indicators,
            "engineered_features": self.engineered_features,
            "is_fitted": self.is_fitted,
            "use_feature_ratios": self.use_feature_ratios,
            "use_robust_scaling": self.use_robust_scaling
        }
        
        joblib.dump(state, path)
        return path
    
    def load(self, path: str = None) -> None:
        """Load pipeline."""
        if path is None:
            path = str(Path(ARTIFACTS_PATH) / "preprocess_pipeline.pkl")
        
        state = joblib.load(path)
        
        self.pipeline = state["pipeline"]
        self.feature_names = state["feature_names"]
        self.numeric_features = state["numeric_features"]
        self.categorical_features = state["categorical_features"]
        self.missing_indicators = state["missing_indicators"]
        self.engineered_features = state.get("engineered_features", [])
        self.is_fitted = state["is_fitted"]
        self.use_feature_ratios = state.get("use_feature_ratios", True)
        self.use_robust_scaling = state.get("use_robust_scaling", True)
    
    def save_manifest(self, path: str = None) -> str:
        """Save feature manifest."""
        if path is None:
            path = str(Path(ARTIFACTS_PATH) / "feature_manifest.json")
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        manifest = {
            "feature_names": self.feature_names,
            "numeric_features": self.numeric_features,
            "categorical_features": self.categorical_features,
            "missing_indicators": self.missing_indicators,
            "engineered_features": self.engineered_features,
            "total_features": len(self.feature_names)
        }
        
        with open(path, "w") as f:
            json.dump(manifest, f, indent=2)
        
        return path


def build_dataset(
    data_path: str,
    train_ratio: float = TRAIN_RATIO,
    val_ratio: float = VAL_RATIO,
    test_ratio: float = TEST_RATIO,
    use_feature_ratios: bool = True,
    use_robust_scaling: bool = True
) -> Dict[str, Any]:
    """Build complete dataset with enhanced preprocessing."""
    pipeline = PreprocessingPipeline(
        use_feature_ratios=use_feature_ratios,
        use_robust_scaling=use_robust_scaling
    )
    
    print("[Preprocessing] Loading and cleaning data...")
    df = pipeline.load_and_clean(data_path)
    
    print("[Preprocessing] Time-aware splitting...")
    train_df, val_df, test_df = pipeline.time_aware_split(df, train_ratio, val_ratio, test_ratio)
    
    print("[Preprocessing] Fitting pipeline on training data...")
    pipeline.fit(train_df)
    
    print("[Preprocessing] Transforming all splits...")
    X_train = pipeline.transform(train_df)
    X_val = pipeline.transform(val_df)
    X_test = pipeline.transform(test_df)
    
    # Select target column
    target_col = "derived_target" if USE_PROBABILITY_TARGET and "derived_target" in train_df.columns else TARGET_COLUMN
    print(f"Using target column: {target_col}")
    
    y_train = train_df[target_col].values
    y_val = val_df[target_col].values
    y_test = test_df[target_col].values
    
    print(f"Target distribution - Train: {y_train.mean():.2%}, Val: {y_val.mean():.2%}, Test: {y_test.mean():.2%}")
    
    # Save artifacts
    artifacts_dir = Path(ARTIFACTS_PATH)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    np.save(artifacts_dir / "X_train.npy", X_train)
    np.save(artifacts_dir / "X_val.npy", X_val)
    np.save(artifacts_dir / "X_test.npy", X_test)
    np.save(artifacts_dir / "y_train.npy", y_train)
    np.save(artifacts_dir / "y_val.npy", y_val)
    np.save(artifacts_dir / "y_test.npy", y_test)
    
    test_meta = test_df[["class_fqn", "repo", "module", "loc"]].copy()
    test_meta.to_csv(artifacts_dir / "test_metadata.csv", index=False)
    
    pipeline_path = pipeline.save()
    manifest_path = pipeline.save_manifest()
    
    return {
        "success": True,
        "message": "Dataset built successfully with enhanced preprocessing",
        "train_info": pipeline.get_split_info(train_df, pd.Series(y_train)),
        "val_info": pipeline.get_split_info(val_df, pd.Series(y_val)),
        "test_info": pipeline.get_split_info(test_df, pd.Series(y_test)),
        "feature_count": len(pipeline.feature_names),
        "engineered_features": len(pipeline.engineered_features),
        "pipeline_path": pipeline_path,
        "manifest_path": manifest_path
    }
