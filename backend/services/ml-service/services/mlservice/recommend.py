"""
Effort-aware recommendation system.
Prioritizes classes based on risk score and effort (LOC).
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.config import ALPHA_EFFORT


def compute_effort_score(
    risk_score: float,
    loc: int,
    alpha: float = ALPHA_EFFORT
) -> float:
    """
    Compute effort-aware score.
    
    Higher score = higher priority for testing.
    Formula: risk_score / (1 + alpha * log1p(loc))
    
    This prioritizes high-risk, low-effort classes.
    
    Args:
        risk_score: Model's risk prediction (0-1)
        loc: Lines of code (effort proxy)
        alpha: Effort penalty factor
        
    Returns:
        Effort-adjusted score
    """
    effort_penalty = 1 + alpha * np.log1p(loc)
    return risk_score / effort_penalty


def generate_recommendations(
    class_fqns: List[str],
    repos: List[str],
    modules: List[str],
    locs: List[int],
    risk_scores: List[float],
    top_k: Optional[int] = 20,
    budget_loc: Optional[int] = None,
    alpha: float = ALPHA_EFFORT
) -> List[Dict[str, Any]]:
    """
    Generate effort-aware recommendations.
    
    Two modes:
    1. top_k: Return top K classes by effort score
    2. budget_loc: Return classes until LOC budget is exhausted
    
    Args:
        class_fqns: List of fully qualified class names
        repos: List of repository names
        modules: List of module names
        locs: List of lines of code
        risk_scores: List of risk scores from model
        top_k: Number of recommendations (None if using budget)
        budget_loc: LOC budget (None if using top_k)
        alpha: Effort penalty factor
        
    Returns:
        List of recommendations sorted by priority
    """
    n = len(class_fqns)
    
    # Compute effort scores
    effort_scores = [
        compute_effort_score(risk_scores[i], locs[i], alpha)
        for i in range(n)
    ]
    
    # Create dataframe for sorting
    df = pd.DataFrame({
        "class_fqn": class_fqns,
        "repo": repos,
        "module": modules,
        "loc": locs,
        "risk_score": risk_scores,
        "effort_score": effort_scores
    })
    
    # Sort by effort score (descending)
    df = df.sort_values("effort_score", ascending=False).reset_index(drop=True)
    
    recommendations = []
    cumulative_loc = 0
    
    for idx, row in df.iterrows():
        # Check budget constraint
        if budget_loc is not None:
            if cumulative_loc + row["loc"] > budget_loc:
                continue
        
        cumulative_loc += row["loc"]
        
        recommendations.append({
            "rank": len(recommendations) + 1,
            "class_fqn": row["class_fqn"],
            "repo": row["repo"],
            "module": row["module"],
            "loc": int(row["loc"]),
            "risk_score": round(float(row["risk_score"]), 4),
            "effort_score": round(float(row["effort_score"]), 4),
            "cumulative_loc": cumulative_loc
        })
        
        # Check top_k constraint
        if top_k is not None and len(recommendations) >= top_k:
            break
    
    return recommendations


def calculate_expected_defects(
    recommendations: List[Dict[str, Any]]
) -> float:
    """
    Calculate expected number of defects in recommendations.
    
    Sum of risk scores gives expected defect count.
    
    Args:
        recommendations: List of recommendation dictionaries
        
    Returns:
        Expected number of defects
    """
    return sum(r["risk_score"] for r in recommendations)


def generate_recommendations_from_test_set(
    model_manager,
    X_test: np.ndarray,
    test_metadata: pd.DataFrame,
    top_k: Optional[int] = 20,
    budget_loc: Optional[int] = None,
    alpha: float = ALPHA_EFFORT
) -> Dict[str, Any]:
    """
    Generate recommendations from test set.
    
    Args:
        model_manager: Trained ModelManager instance
        X_test: Test features
        test_metadata: DataFrame with class_fqn, repo, module, loc
        top_k: Number of recommendations
        budget_loc: LOC budget
        alpha: Effort penalty factor
        
    Returns:
        Dictionary with recommendations and summary stats
    """
    # Get risk scores
    risk_scores = model_manager.predict(X_test)
    
    # Generate recommendations
    recommendations = generate_recommendations(
        class_fqns=test_metadata["class_fqn"].tolist(),
        repos=test_metadata["repo"].tolist(),
        modules=test_metadata["module"].tolist(),
        locs=test_metadata["loc"].tolist(),
        risk_scores=risk_scores.tolist(),
        top_k=top_k,
        budget_loc=budget_loc,
        alpha=alpha
    )
    
    # Calculate summary stats
    total_loc = sum(r["loc"] for r in recommendations)
    expected_defects = calculate_expected_defects(recommendations)
    
    return {
        "success": True,
        "recommendations": recommendations,
        "total_loc": total_loc,
        "expected_defects": round(expected_defects, 2)
    }
