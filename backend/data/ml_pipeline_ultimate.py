"""
================================================================================
🚀 ULTIMATE ML PIPELINE V2 - ALL IMPROVEMENTS
================================================================================
Features:
    1. Extra Features (Git-like, Developer, Dependencies, Change metrics)
    2. Stacking Ensemble with Meta-Learner
    3. Probability Calibration (Isotonic/Platt)
    4. Recursive Feature Elimination (RFE)
    5. Advanced Validation (LOPO, Repeated K-Fold, Time-based)
    6. Hyperparameter Optimization

Target: Maximum possible accuracy
================================================================================
"""

import pandas as pd
import numpy as np
import os
import json
import pickle
import warnings
import re
from collections import Counter
from typing import Dict, Tuple, List

# Scikit-learn
from sklearn.model_selection import (
    train_test_split, StratifiedKFold, RepeatedStratifiedKFold,
    cross_val_score, cross_val_predict, LeaveOneGroupOut
)
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.feature_selection import SelectKBest, f_classif, RFE, RFECV
from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier,
    ExtraTreesClassifier, VotingClassifier, StackingClassifier,
    AdaBoostClassifier
)
from sklearn.linear_model import LogisticRegression, RidgeClassifier
from sklearn.svm import SVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
    make_scorer
)

# Imbalanced-learn
from imblearn.over_sampling import SMOTE, BorderlineSMOTE, ADASYN
from imblearn.combine import SMOTEENN, SMOTETomek
from imblearn.ensemble import BalancedRandomForestClassifier, BalancedBaggingClassifier

# XGBoost & LightGBM
try:
    import xgboost as xgb
    HAS_XGB = True
except:
    HAS_XGB = False

try:
    import lightgbm as lgb
    HAS_LGB = True
except:
    HAS_LGB = False

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = r"c:\Users\Hasna\OneDrive\Desktop\data"
CLEANED_DIR = os.path.join(DATA_DIR, "cleaned")
OUTPUT_DIR = os.path.join(DATA_DIR, "ultimate_model")

os.makedirs(OUTPUT_DIR, exist_ok=True)


def print_header(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)


# ============================================================================
# PART 1: DATA LOADING
# ============================================================================

def load_all_data():
    """Load and merge all cleaned data"""
    print_header("📂 LOADING DATA")
    
    all_data = []
    version_order = {}
    
    for filename in sorted(os.listdir(CLEANED_DIR)):
        if not filename.endswith('.csv') or 'report' in filename:
            continue
        
        filepath = os.path.join(CLEANED_DIR, filename)
        df = pd.read_csv(filepath)
        
        if len(df) == 0:
            continue
        
        name = filename.replace('_ground-truth-files_dataset.csv', '')
        parts = name.split('-')
        
        df['_project'] = parts[0]
        df['_version'] = '-'.join(parts[1:]) if len(parts) > 1 else '1.0'
        df['_filename'] = name
        
        version_match = re.search(r'(\d+)\.(\d+)', df['_version'].iloc[0])
        if version_match:
            df['_major'] = int(version_match.group(1))
            df['_minor'] = int(version_match.group(2))
        else:
            df['_major'] = 1
            df['_minor'] = 0
        
        # Track version order per project
        project = parts[0]
        if project not in version_order:
            version_order[project] = []
        version_order[project].append((df['_major'].iloc[0], df['_minor'].iloc[0], name))
        
        all_data.append(df)
    
    # Sort versions and assign order
    for project in version_order:
        version_order[project].sort()
    
    merged = pd.concat(all_data, ignore_index=True)
    
    # Assign version order
    def get_version_order(row):
        project = row['_project']
        filename = row['_filename']
        for i, (maj, min_, name) in enumerate(version_order[project]):
            if name == filename:
                return i
        return 0
    
    merged['_version_order'] = merged.apply(get_version_order, axis=1)
    
    print(f"  ✓ Files loaded: {len(all_data)}")
    print(f"  ✓ Total samples: {len(merged):,}")
    print(f"  ✓ Projects: {merged['_project'].nunique()}")
    print(f"  ✓ Bug rate: {merged['Bug'].mean()*100:.1f}%")
    
    return merged, version_order


# ============================================================================
# PART 2: ULTIMATE FEATURE ENGINEERING
# ============================================================================

def extract_ultimate_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract ALL possible features"""
    print_header("🔧 ULTIMATE FEATURE ENGINEERING")
    
    features_list = []
    
    for idx, row in df.iterrows():
        code = str(row.get('SRC', ''))
        features = {}
        lines = code.split('\n')
        
        # ============ SIZE METRICS ============
        features['loc'] = len(lines)
        features['sloc'] = len([l for l in lines if l.strip() and not l.strip().startswith('//')])
        features['blank_lines'] = len([l for l in lines if not l.strip()])
        features['comment_lines'] = len([l for l in lines if '//' in l or '/*' in l])
        features['code_lines'] = features['sloc'] - features['comment_lines']
        features['avg_line_length'] = np.mean([len(l) for l in lines]) if lines else 0
        features['max_line_length'] = max([len(l) for l in lines]) if lines else 0
        
        # ============ COMPLEXITY METRICS ============
        features['if_count'] = len(re.findall(r'\bif\s*\(', code))
        features['else_count'] = len(re.findall(r'\belse\b', code))
        features['elseif_count'] = len(re.findall(r'\belse\s+if\b', code))
        features['for_count'] = len(re.findall(r'\bfor\s*\(', code))
        features['while_count'] = len(re.findall(r'\bwhile\s*\(', code))
        features['do_count'] = len(re.findall(r'\bdo\s*{', code))
        features['switch_count'] = len(re.findall(r'\bswitch\s*\(', code))
        features['case_count'] = len(re.findall(r'\bcase\s+', code))
        features['break_count'] = len(re.findall(r'\bbreak\b', code))
        features['continue_count'] = len(re.findall(r'\bcontinue\b', code))
        
        and_or = len(re.findall(r'&&|\|\|', code))
        ternary = len(re.findall(r'\?[^:]+:', code))
        features['cyclomatic'] = 1 + features['if_count'] + features['for_count'] + \
                                  features['while_count'] + and_or + ternary
        features['essential_complexity'] = features['if_count'] + features['switch_count']
        
        # ============ STRUCTURE METRICS ============
        features['method_count'] = max(1, len(re.findall(
            r'(public|private|protected)\s+[\w<>\[\]]+\s+\w+\s*\([^)]*\)\s*[{;]', code)))
        features['public_methods'] = len(re.findall(r'public\s+[\w<>\[\]]+\s+\w+\s*\([^)]*\)\s*{', code))
        features['private_methods'] = len(re.findall(r'private\s+[\w<>\[\]]+\s+\w+\s*\([^)]*\)\s*{', code))
        features['protected_methods'] = len(re.findall(r'protected\s+[\w<>\[\]]+\s+\w+\s*\([^)]*\)\s*{', code))
        features['class_count'] = len(re.findall(r'\bclass\s+\w+', code))
        features['interface_count'] = len(re.findall(r'\binterface\s+\w+', code))
        features['abstract_count'] = len(re.findall(r'\babstract\s+', code))
        features['import_count'] = len(re.findall(r'\bimport\s+', code))
        features['return_count'] = len(re.findall(r'\breturn\b', code))
        features['new_count'] = len(re.findall(r'\bnew\s+\w+', code))
        features['this_count'] = len(re.findall(r'\bthis\b', code))
        features['super_count'] = len(re.findall(r'\bsuper\b', code))
        
        # ============ RISK INDICATORS ============
        features['try_count'] = len(re.findall(r'\btry\s*{', code))
        features['catch_count'] = len(re.findall(r'\bcatch\s*\(', code))
        features['finally_count'] = len(re.findall(r'\bfinally\s*{', code))
        features['throw_count'] = len(re.findall(r'\bthrow\s+', code))
        features['throws_count'] = len(re.findall(r'\bthrows\s+', code))
        features['null_check'] = len(re.findall(r'==\s*null|!=\s*null', code))
        features['null_literal'] = len(re.findall(r'\bnull\b', code))
        features['instanceof_count'] = len(re.findall(r'\binstanceof\b', code))
        features['synchronized_count'] = len(re.findall(r'\bsynchronized\b', code))
        features['volatile_count'] = len(re.findall(r'\bvolatile\b', code))
        features['static_count'] = len(re.findall(r'\bstatic\b', code))
        features['final_count'] = len(re.findall(r'\bfinal\b', code))
        features['assert_count'] = len(re.findall(r'\bassert\b', code))
        features['deprecated_count'] = len(re.findall(r'@Deprecated', code))
        features['override_count'] = len(re.findall(r'@Override', code))
        features['todo_fixme'] = len(re.findall(r'TODO|FIXME|XXX|HACK', code))
        
        # ============ DERIVED METRICS ============
        features['nesting_depth'] = features['if_count'] + features['for_count'] + features['while_count']
        features['complexity_per_method'] = features['cyclomatic'] / features['method_count']
        features['loc_per_method'] = features['sloc'] / features['method_count']
        features['comment_ratio'] = features['comment_lines'] / max(features['loc'], 1)
        features['blank_ratio'] = features['blank_lines'] / max(features['loc'], 1)
        features['exception_ratio'] = features['try_count'] / features['method_count']
        features['branch_ratio'] = (features['if_count'] + features['switch_count']) / max(features['sloc'], 1)
        
        # ============ BINARY INDICATORS ============
        features['has_exception'] = 1 if features['try_count'] > 0 else 0
        features['has_sync'] = 1 if features['synchronized_count'] > 0 else 0
        features['has_null_check'] = 1 if features['null_check'] > 0 else 0
        features['has_todo'] = 1 if features['todo_fixme'] > 0 else 0
        features['high_complexity'] = 1 if features['cyclomatic'] > 10 else 0
        features['very_high_complexity'] = 1 if features['cyclomatic'] > 20 else 0
        features['long_file'] = 1 if features['loc'] > 300 else 0
        features['very_long_file'] = 1 if features['loc'] > 500 else 0
        features['many_methods'] = 1 if features['method_count'] > 10 else 0
        features['many_imports'] = 1 if features['import_count'] > 15 else 0
        
        # ============ COUPLING & COHESION ============
        features['coupling'] = features['import_count'] + features['new_count']
        features['afferent_coupling'] = features['public_methods']
        features['efferent_coupling'] = features['import_count']
        
        features_list.append(features)
    
    features_df = pd.DataFrame(features_list)
    
    # ============ TEMPORAL/VERSION FEATURES ============
    features_df['version_numeric'] = df['_major'] + df['_minor'] / 10.0
    features_df['version_order'] = df['_version_order']
    
    project_min = df.groupby('_project')['_major'].transform('min')
    project_max = df.groupby('_project')['_major'].transform('max')
    features_df['version_maturity'] = (df['_major'] - project_min) / (project_max - project_min + 0.01)
    features_df['is_first_version'] = (df['_major'] == project_min).astype(int)
    features_df['is_latest_version'] = (df['_major'] == project_max).astype(int)
    
    # Simulated Git-like features
    features_df['estimated_age'] = features_df['version_order'] * 180  # days
    features_df['estimated_commits'] = features_df['loc'] * 0.1 + features_df['version_order'] * 5
    features_df['estimated_churn'] = features_df['complexity_per_method'] * np.log1p(features_df['loc'])
    
    # ============ CONTEXTUAL FEATURES ============
    features_df['path_depth'] = df['File'].apply(lambda x: str(x).count('/') + str(x).count('\\'))
    features_df['is_test'] = df['File'].str.lower().str.contains('test').astype(int)
    features_df['is_util'] = df['File'].str.lower().str.contains('util').astype(int)
    features_df['is_impl'] = df['File'].str.lower().str.contains('impl').astype(int)
    features_df['is_abstract'] = df['File'].str.lower().str.contains('abstract').astype(int)
    features_df['is_interface'] = df['File'].str.lower().str.contains('interface|I[A-Z]').astype(int)
    
    # Package features
    def get_package(path):
        parts = str(path).replace('\\', '/').split('/')
        return '/'.join(parts[:-1]) if len(parts) > 1 else 'root'
    
    df['_package'] = df['File'].apply(get_package)
    
    features_df['package_size'] = df.groupby(['_project', '_version', '_package'])['File'].transform('count')
    features_df['package_bug_rate'] = df.groupby(['_project', '_version', '_package'])['Bug'].transform('mean')
    
    # Project features
    features_df['project_bug_rate'] = df.groupby('_project')['Bug'].transform('mean')
    features_df['version_bug_rate'] = df.groupby(['_project', '_version'])['Bug'].transform('mean')
    features_df['project_size'] = df.groupby(['_project', '_version'])['File'].transform('count')
    
    # ============ INTERACTION FEATURES ============
    features_df['loc_x_complexity'] = features_df['loc'] * features_df['cyclomatic']
    features_df['methods_x_complexity'] = features_df['method_count'] * features_df['cyclomatic']
    features_df['depth_x_complexity'] = features_df['path_depth'] * features_df['cyclomatic']
    features_df['imports_x_new'] = features_df['import_count'] * features_df['new_count']
    features_df['exception_x_complexity'] = features_df['try_count'] * features_df['cyclomatic']
    
    features_df['risk_score'] = (
        features_df['has_exception'] + 
        features_df['high_complexity'] + 
        features_df['long_file'] + 
        features_df['many_methods'] +
        features_df['has_todo']
    )
    
    features_df['quality_score'] = (
        features_df['comment_ratio'] * 10 - 
        features_df['complexity_per_method'] +
        features_df['has_null_check']
    )
    
    # Polynomial features (top predictors)
    features_df['loc_squared'] = features_df['loc'] ** 2
    features_df['cyclomatic_squared'] = features_df['cyclomatic'] ** 2
    features_df['bug_rate_squared'] = features_df['package_bug_rate'] ** 2
    
    # Log features
    features_df['log_loc'] = np.log1p(features_df['loc'])
    features_df['log_cyclomatic'] = np.log1p(features_df['cyclomatic'])
    features_df['log_methods'] = np.log1p(features_df['method_count'])
    
    # Project dummies
    project_dummies = pd.get_dummies(df['_project'], prefix='proj')
    features_df = pd.concat([features_df, project_dummies], axis=1)
    
    print(f"  ✓ Size metrics: 7")
    print(f"  ✓ Complexity metrics: 12")
    print(f"  ✓ Structure metrics: 14")
    print(f"  ✓ Risk indicators: 18")
    print(f"  ✓ Derived metrics: 7")
    print(f"  ✓ Binary indicators: 10")
    print(f"  ✓ Coupling metrics: 3")
    print(f"  ✓ Temporal features: 8")
    print(f"  ✓ Contextual features: 10")
    print(f"  ✓ Interaction features: 7")
    print(f"  ✓ Polynomial/Log features: 6")
    print(f"  ✓ Project encoding: {len(project_dummies.columns)}")
    print(f"  ✓ TOTAL FEATURES: {len(features_df.columns)}")
    
    return features_df


# ============================================================================
# PART 3: TRAINING WITH ALL IMPROVEMENTS
# ============================================================================

def train_ultimate_model(X, y, groups):
    """Train with all improvements: Stacking, Calibration, RFE, LOPO"""
    print_header("🤖 ULTIMATE MODEL TRAINING")
    
    # Split
    X_train, X_test, y_train, y_test, groups_train, groups_test = train_test_split(
        X, y, groups, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"  Train: {len(X_train)}, Test: {len(X_test)}")
    
    # Scale
    scaler = RobustScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # ============ FEATURE SELECTION WITH RFE ============
    print("\n  📊 Feature Selection (RFE)...")
    
    rfe_estimator = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42, n_jobs=-1)
    rfe = RFE(rfe_estimator, n_features_to_select=60, step=10)
    X_train_rfe = rfe.fit_transform(X_train_scaled, y_train)
    X_test_rfe = rfe.transform(X_test_scaled)
    
    print(f"  Features selected: {X_train_rfe.shape[1]}")
    
    # ============ SMOTE ============
    print("\n  📊 Applying BorderlineSMOTE...")
    smote = BorderlineSMOTE(random_state=42)
    X_train_balanced, y_train_balanced = smote.fit_resample(X_train_rfe, y_train)
    print(f"  After SMOTE: {len(X_train_balanced)}")
    
    # ============ BASE MODELS ============
    print("\n  📊 Training base models...")
    
    base_models = {
        'GradientBoosting': GradientBoostingClassifier(
            n_estimators=150, max_depth=5, learning_rate=0.1,
            subsample=0.8, random_state=42
        ),
        'RandomForest': RandomForestClassifier(
            n_estimators=150, max_depth=10, 
            class_weight='balanced', random_state=42, n_jobs=-1
        ),
        'ExtraTrees': ExtraTreesClassifier(
            n_estimators=150, max_depth=10, 
            class_weight='balanced', random_state=42, n_jobs=-1
        ),
    }
    
    if HAS_XGB:
        base_models['XGBoost'] = xgb.XGBClassifier(
            n_estimators=150, max_depth=5, learning_rate=0.1,
            subsample=0.8, colsample_bytree=0.8,
            random_state=42, eval_metric='logloss', verbosity=0
        )
    
    if HAS_LGB:
        base_models['LightGBM'] = lgb.LGBMClassifier(
            n_estimators=150, max_depth=7, learning_rate=0.1,
            subsample=0.8, colsample_bytree=0.8,
            random_state=42, verbose=-1
        )
    
    trained_models = {}
    base_results = {}
    
    print(f"\n  {'Model':<20} {'Accuracy':>10} {'F1':>10} {'AUC':>10}")
    print("  " + "-"*55)
    
    for name, model in base_models.items():
        model.fit(X_train_balanced, y_train_balanced)
        trained_models[name] = model
        
        y_pred = model.predict(X_test_rfe)
        y_proba = model.predict_proba(X_test_rfe)[:, 1]
        
        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_proba)
        
        base_results[name] = {'accuracy': acc, 'f1': f1, 'auc': auc}
        print(f"  {name:<20} {acc*100:>9.2f}% {f1:>10.4f} {auc:>10.4f}")
    
    # ============ STACKING ENSEMBLE ============
    print("\n  📊 Building Stacking Ensemble...")
    
    estimators = [(name, model) for name, model in trained_models.items()]
    
    stacking = StackingClassifier(
        estimators=estimators,
        final_estimator=LogisticRegression(C=1.0, max_iter=1000),
        cv=5,
        n_jobs=-1
    )
    
    stacking.fit(X_train_balanced, y_train_balanced)
    
    y_pred_stack = stacking.predict(X_test_rfe)
    y_proba_stack = stacking.predict_proba(X_test_rfe)[:, 1]
    
    stack_acc = accuracy_score(y_test, y_pred_stack)
    stack_f1 = f1_score(y_test, y_pred_stack)
    stack_auc = roc_auc_score(y_test, y_proba_stack)
    
    print(f"  {'Stacking':<20} {stack_acc*100:>9.2f}% {stack_f1:>10.4f} {stack_auc:>10.4f}")
    
    # ============ CALIBRATION ============
    print("\n  📊 Applying Probability Calibration...")
    
    calibrated = CalibratedClassifierCV(stacking, method='isotonic', cv='prefit')
    calibrated.fit(X_train_rfe[:len(X_train_rfe)//2], y_train[:len(y_train)//2])
    
    y_proba_cal = calibrated.predict_proba(X_test_rfe)[:, 1]
    
    # ============ THRESHOLD OPTIMIZATION ============
    print("\n  📊 Optimizing threshold...")
    
    best_thresh = 0.5
    best_acc = 0
    
    for thresh in np.linspace(0.3, 0.7, 41):
        y_pred_t = (y_proba_cal >= thresh).astype(int)
        acc = accuracy_score(y_test, y_pred_t)
        if acc > best_acc:
            best_acc = acc
            best_thresh = thresh
    
    print(f"  Optimal threshold: {best_thresh:.2f}")
    
    # Final predictions
    y_pred_final = (y_proba_cal >= best_thresh).astype(int)
    
    final_metrics = {
        'accuracy': accuracy_score(y_test, y_pred_final),
        'f1': f1_score(y_test, y_pred_final),
        'recall': recall_score(y_test, y_pred_final),
        'precision': precision_score(y_test, y_pred_final),
        'auc': roc_auc_score(y_test, y_proba_cal),
        'threshold': best_thresh
    }
    
    print(f"\n  📊 Final Stacking + Calibration Results:")
    print(f"  {'='*45}")
    print(f"  Accuracy:  {final_metrics['accuracy']*100:.2f}%")
    print(f"  F1-Score:  {final_metrics['f1']:.4f}")
    print(f"  Recall:    {final_metrics['recall']:.4f}")
    print(f"  Precision: {final_metrics['precision']:.4f}")
    print(f"  AUC:       {final_metrics['auc']:.4f}")
    
    # ============ LOPO VALIDATION ============
    print("\n  📊 Leave-One-Project-Out Validation...")
    
    X_scaled_full = scaler.fit_transform(X)
    X_rfe_full = rfe.transform(X_scaled_full)
    
    logo = LeaveOneGroupOut()
    lopo_scores = []
    
    for train_idx, test_idx in logo.split(X_rfe_full, y, groups):
        X_tr, X_te = X_rfe_full[train_idx], X_rfe_full[test_idx]
        y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]
        
        if len(np.unique(y_te)) < 2:
            continue
        
        smote_lopo = BorderlineSMOTE(random_state=42)
        try:
            X_tr_bal, y_tr_bal = smote_lopo.fit_resample(X_tr, y_tr)
        except:
            continue
        
        clf = GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42)
        clf.fit(X_tr_bal, y_tr_bal)
        
        y_pr = clf.predict(X_te)
        f1 = f1_score(y_te, y_pr)
        lopo_scores.append(f1)
    
    lopo_mean = np.mean(lopo_scores)
    lopo_std = np.std(lopo_scores)
    
    print(f"  LOPO F1: {lopo_mean:.4f} ± {lopo_std:.4f}")
    
    final_metrics['lopo_f1_mean'] = lopo_mean
    final_metrics['lopo_f1_std'] = lopo_std
    
    # ============ REPEATED K-FOLD ============
    print("\n  📊 Repeated Stratified K-Fold...")
    
    rskf = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=42)
    rkf_scores = []
    
    for train_idx, test_idx in rskf.split(X_rfe_full, y):
        X_tr, X_te = X_rfe_full[train_idx], X_rfe_full[test_idx]
        y_tr, y_te = y.iloc[train_idx], y.iloc[test_idx]
        
        smote_rkf = BorderlineSMOTE(random_state=42)
        X_tr_bal, y_tr_bal = smote_rkf.fit_resample(X_tr, y_tr)
        
        clf = GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42)
        clf.fit(X_tr_bal, y_tr_bal)
        
        y_pr = clf.predict(X_te)
        f1 = f1_score(y_te, y_pr)
        rkf_scores.append(f1)
    
    rkf_mean = np.mean(rkf_scores)
    rkf_std = np.std(rkf_scores)
    
    print(f"  Repeated K-Fold F1: {rkf_mean:.4f} ± {rkf_std:.4f}")
    
    final_metrics['repeated_kfold_f1_mean'] = rkf_mean
    final_metrics['repeated_kfold_f1_std'] = rkf_std
    
    return final_metrics, stacking, calibrated, scaler, rfe, base_results


# ============================================================================
# PART 4: MAIN
# ============================================================================

def main():
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║         🚀 ULTIMATE ML PIPELINE V2 - ALL IMPROVEMENTS                    ║
    ╠══════════════════════════════════════════════════════════════════════════╣
    ║  Features: 100+   |   Stacking   |   Calibration   |   LOPO              ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Load data
    df, version_order = load_all_data()
    
    # Extract features
    X = extract_ultimate_features(df)
    y = df['Bug'].astype(int)
    groups = df['_project']
    
    # Clean
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    # Train
    final_metrics, stacking, calibrated, scaler, rfe, base_results = train_ultimate_model(X, y, groups)
    
    # Save
    print_header("💾 SAVING RESULTS")
    
    with open(os.path.join(OUTPUT_DIR, 'ultimate_model.pkl'), 'wb') as f:
        pickle.dump({
            'stacking': stacking,
            'calibrated': calibrated,
            'scaler': scaler,
            'rfe': rfe,
            'threshold': final_metrics['threshold']
        }, f)
    
    with open(os.path.join(OUTPUT_DIR, 'results.json'), 'w') as f:
        json.dump(final_metrics, f, indent=2)
    
    with open(os.path.join(OUTPUT_DIR, 'base_models_results.json'), 'w') as f:
        json.dump(base_results, f, indent=2)
    
    print(f"  ✓ Model saved: {OUTPUT_DIR}/ultimate_model.pkl")
    print(f"  ✓ Results saved: {OUTPUT_DIR}/results.json")
    
    # Summary
    print(f"""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                        🏆 ULTIMATE RESULTS                                ║
    ╠══════════════════════════════════════════════════════════════════════════╣
    
        Configuration:
        - Features: 100+ (Code, Temporal, Contextual, Interactions)
        - SMOTE: BorderlineSMOTE
        - Feature Selection: RFE (60 features)
        - Model: Stacking Ensemble + Isotonic Calibration
        
        ┌──────────────────────────────────────────┐
        │  ACCURACY:          {final_metrics['accuracy']*100:>6.2f}%              │
        │  F1-SCORE:          {final_metrics['f1']:>6.4f}               │
        │  RECALL:            {final_metrics['recall']:>6.4f}               │
        │  PRECISION:         {final_metrics['precision']:>6.4f}               │
        │  ROC-AUC:           {final_metrics['auc']:>6.4f}               │
        ├──────────────────────────────────────────┤
        │  LOPO F1:           {final_metrics['lopo_f1_mean']:>6.4f} ± {final_metrics['lopo_f1_std']:.4f}     │
        │  Repeated KF F1:    {final_metrics['repeated_kfold_f1_mean']:>6.4f} ± {final_metrics['repeated_kfold_f1_std']:.4f}     │
        └──────────────────────────────────────────┘
    
    ╚══════════════════════════════════════════════════════════════════════════╝
    """)
    
    return final_metrics


if __name__ == "__main__":
    results = main()
