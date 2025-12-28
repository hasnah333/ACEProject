"""
Enhanced evaluation metrics for ML Service.
Includes Precision@K, Recall@K, F1@K, NDCG, Lift, and Popt@20.
"""
import numpy as np
from typing import Optional, List


def precision_at_k(y_true: np.ndarray, y_scores: np.ndarray, k: int) -> float:
    """
    Calculate Precision@K.
    Precision@K = (# true positives in top K) / K
    """
    if k <= 0:
        raise ValueError("k must be positive")
    
    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores)
    
    n = min(k, len(y_scores))
    top_k_indices = np.argsort(y_scores)[::-1][:n]
    true_positives = np.sum(y_true[top_k_indices])
    
    return float(true_positives / n)


def recall_at_k(y_true: np.ndarray, y_scores: np.ndarray, k: int) -> float:
    """
    Calculate Recall@K.
    Recall@K = (# true positives in top K) / (total positives)
    """
    if k <= 0:
        raise ValueError("k must be positive")
    
    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores)
    
    total_positives = np.sum(y_true)
    if total_positives == 0:
        return 0.0
    
    n = min(k, len(y_scores))
    top_k_indices = np.argsort(y_scores)[::-1][:n]
    true_positives = np.sum(y_true[top_k_indices])
    
    return float(true_positives / total_positives)


def f1_at_k(y_true: np.ndarray, y_scores: np.ndarray, k: int) -> float:
    """
    Calculate F1 Score@K.
    F1@K = 2 * (Precision@K * Recall@K) / (Precision@K + Recall@K)
    """
    prec = precision_at_k(y_true, y_scores, k)
    rec = recall_at_k(y_true, y_scores, k)
    
    if prec + rec == 0:
        return 0.0
    
    return 2 * (prec * rec) / (prec + rec)


def dcg_at_k(relevance: np.ndarray, k: int) -> float:
    """
    Calculate Discounted Cumulative Gain at K.
    DCG@K = sum(rel_i / log2(i + 1)) for i = 1 to K
    """
    relevance = np.asarray(relevance)[:k]
    n = len(relevance)
    
    if n == 0:
        return 0.0
    
    positions = np.arange(1, n + 1)
    discounts = np.log2(positions + 1)
    
    return float(np.sum(relevance / discounts))


def ndcg_at_k(y_true: np.ndarray, y_scores: np.ndarray, k: int) -> float:
    """
    Calculate Normalized Discounted Cumulative Gain at K.
    NDCG@K = DCG@K / IDCG@K (Ideal DCG)
    """
    if k <= 0:
        raise ValueError("k must be positive")
    
    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores)
    
    n = min(k, len(y_scores))
    
    # Get model ranking
    model_order = np.argsort(y_scores)[::-1][:n]
    model_relevance = y_true[model_order]
    
    # Get ideal ranking (sort by true labels)
    ideal_order = np.argsort(y_true)[::-1][:n]
    ideal_relevance = y_true[ideal_order]
    
    dcg = dcg_at_k(model_relevance, n)
    idcg = dcg_at_k(ideal_relevance, n)
    
    if idcg == 0:
        return 0.0
    
    return float(dcg / idcg)


def lift_at_k(y_true: np.ndarray, y_scores: np.ndarray, k: int) -> float:
    """
    Calculate Lift at K.
    Lift@K = (Precision@K) / (baseline positive rate)
    
    Measures how much better than random the model is.
    Lift > 1 means better than random, < 1 means worse.
    """
    if k <= 0:
        raise ValueError("k must be positive")
    
    y_true = np.asarray(y_true)
    
    baseline = np.mean(y_true)
    if baseline == 0:
        return 0.0
    
    prec_k = precision_at_k(y_true, y_scores, k)
    
    return float(prec_k / baseline)


def expected_lift_curve(
    y_true: np.ndarray, 
    y_scores: np.ndarray, 
    n_points: int = 20
) -> List[dict]:
    """
    Calculate lift curve at various percentages.
    
    Returns list of {percent, lift, precision, recall} dicts.
    """
    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores)
    
    n = len(y_true)
    baseline = np.mean(y_true)
    
    results = []
    percentages = np.linspace(0.05, 1.0, n_points)
    
    for pct in percentages:
        k = max(1, int(n * pct))
        prec = precision_at_k(y_true, y_scores, k)
        rec = recall_at_k(y_true, y_scores, k)
        lift = prec / baseline if baseline > 0 else 0
        
        results.append({
            "percent": round(pct * 100, 1),
            "k": k,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "lift": round(lift, 2)
        })
    
    return results


def popt_at_percent(
    y_true: np.ndarray, 
    y_scores: np.ndarray, 
    effort: np.ndarray,
    percent: float = 20.0
) -> float:
    """
    Calculate Popt@percent (Percentage of Optimal).
    Effort-aware metric measuring defect detection efficiency.
    """
    y_true = np.asarray(y_true)
    y_scores = np.asarray(y_scores)
    effort = np.asarray(effort)
    
    if len(y_true) == 0:
        return 0.0
    
    total_defects = np.sum(y_true)
    total_effort = np.sum(effort)
    
    if total_defects == 0 or total_effort == 0:
        return 0.0
    
    target_effort = total_effort * (percent / 100.0)
    
    # Model ordering
    model_order = np.argsort(y_scores)[::-1]
    cum_effort = 0
    cum_defects_model = 0
    for idx in model_order:
        if cum_effort >= target_effort:
            break
        cum_effort += effort[idx]
        cum_defects_model += y_true[idx]
    
    # Optimal ordering
    with np.errstate(divide='ignore', invalid='ignore'):
        defect_density = np.where(effort > 0, y_true / effort, 0)
    optimal_order = np.argsort(defect_density)[::-1]
    
    cum_effort = 0
    cum_defects_optimal = 0
    for idx in optimal_order:
        if cum_effort >= target_effort:
            break
        cum_effort += effort[idx]
        cum_defects_optimal += y_true[idx]
    
    # Worst ordering
    worst_order = np.argsort(defect_density)
    cum_effort = 0
    cum_defects_worst = 0
    for idx in worst_order:
        if cum_effort >= target_effort:
            break
        cum_effort += effort[idx]
        cum_defects_worst += y_true[idx]
    
    if cum_defects_optimal == cum_defects_worst:
        return 1.0
    
    popt = 1 - (cum_defects_optimal - cum_defects_model) / (cum_defects_optimal - cum_defects_worst)
    
    return float(np.clip(popt, 0.0, 1.0))


def compute_all_metrics(
    y_true: np.ndarray,
    y_scores: np.ndarray,
    effort: Optional[np.ndarray] = None,
    k_values: list = [50, 100],
    popt_percent: float = 20.0
) -> dict:
    """
    Compute all evaluation metrics including new ones.
    """
    from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
    
    metrics = {}
    
    # Standard metrics
    try:
        metrics["auc_roc"] = roc_auc_score(y_true, y_scores)
    except ValueError:
        metrics["auc_roc"] = 0.0
    
    try:
        metrics["auc_pr"] = average_precision_score(y_true, y_scores)
    except ValueError:
        metrics["auc_pr"] = 0.0
    
    metrics["brier_score"] = brier_score_loss(y_true, y_scores)
    
    # Precision@K, Recall@K, F1@K, NDCG@K, Lift@K
    for k in k_values:
        metrics[f"precision_at_{k}"] = precision_at_k(y_true, y_scores, k)
        metrics[f"recall_at_{k}"] = recall_at_k(y_true, y_scores, k)
        metrics[f"f1_at_{k}"] = f1_at_k(y_true, y_scores, k)
        metrics[f"ndcg_at_{k}"] = ndcg_at_k(y_true, y_scores, k)
        metrics[f"lift_at_{k}"] = lift_at_k(y_true, y_scores, k)
    
    # Popt
    if effort is not None:
        metrics[f"popt_{int(popt_percent)}"] = popt_at_percent(
            y_true, y_scores, effort, popt_percent
        )
    else:
        metrics[f"popt_{int(popt_percent)}"] = 0.0
    
    return metrics


def get_ranking_metrics_summary(y_true: np.ndarray, y_scores: np.ndarray) -> dict:
    """
    Get a comprehensive summary of ranking metrics.
    """
    baseline = np.mean(y_true)
    total_positive = np.sum(y_true)
    
    summary = {
        "baseline_rate": round(baseline, 4),
        "total_samples": len(y_true),
        "total_positive": int(total_positive),
        "metrics_at_k": {}
    }
    
    for k in [10, 25, 50, 100, 200]:
        if k <= len(y_true):
            summary["metrics_at_k"][k] = {
                "precision": round(precision_at_k(y_true, y_scores, k), 4),
                "recall": round(recall_at_k(y_true, y_scores, k), 4),
                "f1": round(f1_at_k(y_true, y_scores, k), 4),
                "ndcg": round(ndcg_at_k(y_true, y_scores, k), 4),
                "lift": round(lift_at_k(y_true, y_scores, k), 2)
            }
    
    return summary
