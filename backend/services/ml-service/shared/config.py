"""
Configuration module for ML Service.
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_PATH = os.environ.get("DATA_PATH", str(BASE_DIR / "data"))
ARTIFACTS_PATH = os.environ.get("ARTIFACTS_PATH", str(BASE_DIR / "artifacts"))
REPORTS_PATH = os.environ.get("REPORTS_PATH", str(BASE_DIR / "reports"))

# Ensure directories exist
Path(ARTIFACTS_PATH).mkdir(parents=True, exist_ok=True)
Path(REPORTS_PATH).mkdir(parents=True, exist_ok=True)
Path(REPORTS_PATH, "figures").mkdir(parents=True, exist_ok=True)

# Dataset files
MAIN_DATASET = os.path.join(DATA_PATH, "software_class_metrics_synth.csv")
INFERENCE_DATASET = os.path.join(DATA_PATH, "inference_payload_example.csv")

# Feature configuration
ID_COLUMNS = ["repo", "module", "language", "class_fqn", "snapshot_date"]
CATEGORICAL_COLUMNS = ["repo", "module", "language"]

# Target configuration
# Use defect_probability_latent with threshold for better signal (synthetic data)
# Set to True to use probability-based target, False to use original binary
USE_PROBABILITY_TARGET = True
PROBABILITY_THRESHOLD = 0.008  # ~40-50% positive rate for stronger signal
TARGET_COLUMN = "defect_next_30d"  # Original target
PROBABILITY_COLUMN = "defect_probability_latent"  # For thresholding

# Columns to exclude from features (will be removed or used as target)
LEAKAGE_COLUMNS = ["defect_count_next_30d"]  # Keep probability for target derivation

# Feature engineering
USE_POLYNOMIAL_FEATURES = True  # Add interaction terms

# Numeric features (will be auto-detected, but these are expected)
EXPECTED_NUMERIC_FEATURES = [
    "loc", "cyclomatic_complexity", "wmc", "dit", "noc", "cbo", "rfc", "lcom",
    "fan_in", "fan_out", "code_smells", "num_commits_30d", "added_loc_30d",
    "deleted_loc_30d", "num_authors_30d", "days_since_last_change",
    "bugfix_commits_90d", "issues_90d", "line_coverage_pct", "branch_coverage_pct",
    "mutation_score_pct", "tests_failed_30d", "flaky_rate"
]

# Preprocessing configuration
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# Clip bounds for coverage and flaky rate
COVERAGE_MIN = 0.0
COVERAGE_MAX = 100.0
FLAKY_MIN = 0.0
FLAKY_MAX = 1.0

# Model configuration
RANDOM_STATE = 42
K_VALUES = [50, 100]  # For Precision@K and Recall@K
POPT_EFFORT_PERCENT = 20  # Popt@20

# Recommendation configuration
ALPHA_EFFORT = 0.1  # For effort-aware scoring: score / (1 + alpha * log1p(loc))

# Model names
MODEL_NAMES = {
    "logistic": "LogisticRegression",
    "random_forest": "RandomForestClassifier", 
    "hist_gradient": "HistGradientBoostingClassifier",
    "xgboost": "XGBoostClassifier",
    "lightgbm": "LightGBMClassifier",
    "stacking": "StackingEnsemble",
    "voting": "VotingEnsemble"
}
