"""Visualize content of artifact files."""
import joblib
import numpy as np
import json
from pathlib import Path

print("=" * 60)
print("CONTENU DES FICHIERS ARTIFACTS")
print("=" * 60)

# 1. Feature Manifest (JSON)
print("\n[1] feature_manifest.json")
print("-" * 40)
with open("artifacts/feature_manifest.json") as f:
    manifest = json.load(f)
print(f"Total features: {manifest['total_features']}")
print(f"Numeric features: {len(manifest['numeric_features'])}")
print(f"Categorical features: {len(manifest['categorical_features'])}")
print(f"Engineered features: {len(manifest.get('engineered_features', []))}")
print(f"\nTop 10 features:")
for i, feat in enumerate(manifest["feature_names"][:10], 1):
    print(f"  {i}. {feat}")

# 2. Models Metadata
print("\n[2] models_metadata.pkl")
print("-" * 40)
metadata = joblib.load("artifacts/models_metadata.pkl")
print(f"Best model: {metadata['best_model_name']}")
print(f"Is trained: {metadata['is_trained']}")
print(f"Models evaluated: {list(metadata['metrics'].keys())}")

# 3. Modeles disponibles
print("\n[3] Modeles Entraines (.pkl)")
print("-" * 40)
for pkl in Path("artifacts").glob("model_*.pkl"):
    if "metadata" not in pkl.name:
        try:
            model = joblib.load(pkl)
            print(f"  {pkl.name}: {type(model).__name__}")
        except:
            print(f"  {pkl.name}: (chargement)")

# 4. Donnees NumPy
print("\n[4] Donnees NumPy (.npy)")
print("-" * 40)
for npy in Path("artifacts").glob("*.npy"):
    data = np.load(npy)
    print(f"  {npy.name}: shape={data.shape}, dtype={data.dtype}")

# 5. y_test distribution
print("\n[5] Distribution y_test")
print("-" * 40)
y_test = np.load("artifacts/y_test.npy")
print(f"  Negatifs (0): {(y_test == 0).sum()}")
print(f"  Positifs (1): {(y_test == 1).sum()}")
print(f"  Taux positif: {y_test.mean():.2%}")

# 6. Sample predictions
print("\n[6] Exemple de predictions")
print("-" * 40)
X_test = np.load("artifacts/X_test.npy")
model = joblib.load("artifacts/model_logistic.pkl")
scores = model.predict_proba(X_test[:5])[:, 1]
print("  Premiers 5 risk scores:")
for i, score in enumerate(scores):
    print(f"    Sample {i+1}: {score:.4f} ({score*100:.1f}%)")

print("\n" + "=" * 60)
