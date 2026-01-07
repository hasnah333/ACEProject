"""
================================================================================
ML FEATURE ENGINEERING PIPELINE - DATASET PROMISE
================================================================================
Expert: ML Engineer
Objectif: Préparer les données pour la prédiction de défauts logiciels

ARCHITECTURE DU PIPELINE:
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   DONNÉES   │───►│    SPLIT    │───►│ FIT sur    │───►│ TRANSFORM   │  │
│  │   BRUTES    │    │ TRAIN/TEST  │    │ TRAIN only │    │    BOTH     │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                           │                   │                   │         │
│                           ▼                   ▼                   ▼         │
│                     ⚠️ DATA LEAKAGE      ✅ SAFE           ✅ SAFE         │
│                     SI FIT AVANT SPLIT                                      │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

Auteur: ML Engineer
Date: 2026-01-05
================================================================================
"""

import pandas as pd
import numpy as np
import os
import re
import hashlib
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path
import warnings
import logging
from collections import Counter
import gc

# Scikit-learn imports
from sklearn.model_selection import train_test_split, StratifiedKFold, LeaveOneGroupOut
from sklearn.preprocessing import (
    StandardScaler, MinMaxScaler, RobustScaler,
    LabelEncoder, OneHotEncoder, OrdinalEncoder
)
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.compose import ColumnTransformer
from sklearn.base import BaseEstimator, TransformerMixin

warnings.filterwarnings('ignore')

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# SECTION 1: CONFIGURATION
# ============================================================================

@dataclass
class MLConfig:
    """Configuration du pipeline ML"""
    
    # Chemins
    input_dir: str = r"c:\Users\Hasna\OneDrive\Desktop\data\cleaned"
    output_dir: str = r"c:\Users\Hasna\OneDrive\Desktop\data\ml_ready"
    
    # Colonnes
    target_column: str = 'Bug'
    id_column: str = 'File'
    text_column: str = 'SRC'
    
    # Colonnes de métadonnées (ajoutées par le pipeline de nettoyage)
    metadata_columns: List[str] = field(default_factory=lambda: [
        '_project', '_version', '_source_file'
    ])
    
    # Split configuration
    test_size: float = 0.2
    random_state: int = 42
    stratify: bool = True
    
    # Feature engineering
    extract_code_metrics: bool = True
    use_tfidf: bool = True
    tfidf_max_features: int = 500
    
    # Normalisation
    scaler_type: str = 'robust'  # 'standard', 'minmax', 'robust'
    
    # Fichiers à exclure
    exclude_files: List[str] = field(default_factory=list)


# ============================================================================
# SECTION 2: HARMONISATION DES SCHÉMAS
# ============================================================================

class SchemaHarmonizer:
    """
    ÉTAPE 1: HARMONISATION DES COLONNES ET SCHÉMAS
    
    POURQUOI C'EST NÉCESSAIRE:
    ─────────────────────────────────────────────────────────────────────────
    - Les fichiers CSV de différentes sources peuvent avoir des noms de 
      colonnes différents (case, espaces, typos)
    - Les types de données peuvent varier d'un fichier à l'autre
    - Certaines colonnes peuvent être manquantes dans certains fichiers
    
    QUAND L'APPLIQUER:
    ─────────────────────────────────────────────────────────────────────────
    ✅ AVANT le split train/test
    - C'est une transformation structurelle, pas statistique
    - Pas de risque de data leakage
    """
    
    def __init__(self, expected_schema: Dict[str, str]):
        """
        Args:
            expected_schema: Dict {nom_colonne: type_attendu}
        """
        self.expected_schema = expected_schema
        self.column_mappings = {}
        
    def _normalize_column_name(self, col: str) -> str:
        """Normalise un nom de colonne"""
        # Minuscules, remplacer espaces par underscore
        normalized = col.strip().lower().replace(' ', '_')
        # Supprimer caractères spéciaux
        normalized = re.sub(r'[^a-z0-9_]', '', normalized)
        return normalized
    
    def _detect_column_mapping(self, df: pd.DataFrame) -> Dict[str, str]:
        """Détecte automatiquement le mapping des colonnes"""
        mapping = {}
        df_cols_normalized = {self._normalize_column_name(c): c for c in df.columns}
        
        for expected_col in self.expected_schema.keys():
            expected_normalized = self._normalize_column_name(expected_col)
            
            # Correspondance exacte (après normalisation)
            if expected_normalized in df_cols_normalized:
                mapping[df_cols_normalized[expected_normalized]] = expected_col
            else:
                # Recherche par similarité (Levenshtein simplifié)
                for orig, norm in df_cols_normalized.items():
                    if expected_normalized in norm or norm in expected_normalized:
                        mapping[orig] = expected_col
                        break
        
        return mapping
    
    def harmonize(self, df: pd.DataFrame, source_name: str = "") -> pd.DataFrame:
        """
        Harmonise un DataFrame selon le schéma attendu
        
        LOGIQUE MÉTIER:
        1. Détecter le mapping des colonnes
        2. Renommer les colonnes
        3. Convertir les types
        4. Ajouter colonnes manquantes avec valeurs par défaut
        """
        logger.info(f"Harmonisation du schéma pour: {source_name}")
        
        # Détection du mapping
        mapping = self._detect_column_mapping(df)
        self.column_mappings[source_name] = mapping
        
        # Renommage des colonnes
        df = df.rename(columns=mapping)
        
        # Conversion des types
        for col, expected_type in self.expected_schema.items():
            if col in df.columns:
                try:
                    if expected_type == 'bool':
                        df[col] = df[col].astype(bool)
                    elif expected_type == 'int':
                        df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
                    elif expected_type == 'float':
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    elif expected_type == 'str':
                        df[col] = df[col].astype(str)
                    elif expected_type == 'category':
                        df[col] = df[col].astype('category')
                except Exception as e:
                    logger.warning(f"Conversion échouée pour {col}: {e}")
            else:
                # Ajouter colonne manquante avec valeur par défaut
                if expected_type == 'bool':
                    df[col] = False
                elif expected_type in ['int', 'float']:
                    df[col] = np.nan
                else:
                    df[col] = ''
        
        return df


# ============================================================================
# SECTION 3: FEATURE ENGINEERING - CODE SOURCE
# ============================================================================

class CodeMetricsExtractor(BaseEstimator, TransformerMixin):
    """
    ÉTAPE 4: CRÉATION DE FEATURES PERTINENTES (Feature Engineering)
    
    POURQUOI C'EST NÉCESSAIRE:
    ─────────────────────────────────────────────────────────────────────────
    - Le code source brut ne peut pas être utilisé directement par les modèles ML
    - Les métriques de code (LOC, complexité, etc.) sont corrélées aux défauts
    - Transformation d'information non-structurée en features numériques
    
    QUAND L'APPLIQUER:
    ─────────────────────────────────────────────────────────────────────────
    ✅ AVANT le split train/test (pas de statistiques globales)
    - Ces métriques sont calculées individuellement par fichier
    - Pas de risque de data leakage car pas d'agrégation
    
    ⚠️ EXCEPTION: Si on calcule des percentiles ou moyennes globales,
       alors il faut appliquer APRÈS le split
    """
    
    def __init__(self):
        self.feature_names = []
        
    def fit(self, X, y=None):
        """Fit n'est pas nécessaire pour les métriques de code"""
        return self
    
    def transform(self, X: pd.Series) -> pd.DataFrame:
        """
        Extrait les métriques de code depuis le code source Java
        
        Features extraites:
        - Métriques de taille (LOC, SLOC, commentaires)
        - Métriques de complexité (branches, boucles)
        - Métriques structurelles (classes, méthodes)
        """
        features = []
        
        for code in X:
            metrics = self._extract_metrics(str(code))
            features.append(metrics)
        
        df = pd.DataFrame(features)
        self.feature_names = list(df.columns)
        return df
    
    def _extract_metrics(self, code: str) -> Dict[str, float]:
        """
        Extrait les métriques d'un fichier de code Java
        
        MÉTRIQUES CK-LIKE:
        - WMC (Weighted Methods per Class) approximé
        - DIT (Depth of Inheritance Tree) simplifié
        - NOC (Number of Children) - nécessite contexte global
        - CBO (Coupling Between Objects) approximé
        - RFC (Response For Class) approximé
        - LCOM (Lack of Cohesion in Methods) simplifié
        """
        metrics = {}
        
        lines = code.split('\n')
        
        # =====================================================================
        # MÉTRIQUES DE TAILLE
        # =====================================================================
        
        # LOC - Lines of Code
        metrics['loc'] = len(lines)
        
        # SLOC - Source Lines of Code (non-vides, non-commentaires)
        sloc = 0
        comment_lines = 0
        blank_lines = 0
        
        in_multiline_comment = False
        for line in lines:
            stripped = line.strip()
            
            if not stripped:
                blank_lines += 1
                continue
            
            # Gestion des commentaires multi-lignes
            if '/*' in stripped:
                in_multiline_comment = True
            if '*/' in stripped:
                in_multiline_comment = False
                comment_lines += 1
                continue
            
            if in_multiline_comment or stripped.startswith('//') or stripped.startswith('*'):
                comment_lines += 1
            else:
                sloc += 1
        
        metrics['sloc'] = sloc
        metrics['comment_lines'] = comment_lines
        metrics['blank_lines'] = blank_lines
        metrics['comment_ratio'] = comment_lines / max(metrics['loc'], 1)
        
        # =====================================================================
        # MÉTRIQUES DE COMPLEXITÉ
        # =====================================================================
        
        # Branches conditionnelles (approximation de McCabe CC)
        if_count = len(re.findall(r'\bif\s*\(', code))
        else_count = len(re.findall(r'\belse\b', code))
        switch_count = len(re.findall(r'\bswitch\s*\(', code))
        case_count = len(re.findall(r'\bcase\s+', code))
        ternary_count = len(re.findall(r'\?.*:', code))
        
        metrics['if_count'] = if_count
        metrics['else_count'] = else_count
        metrics['switch_count'] = switch_count
        metrics['case_count'] = case_count
        metrics['ternary_count'] = ternary_count
        
        # Complexité cyclomatique approximée
        # CC = 1 + conditions (if, else if, case, &&, ||, ?)
        and_or_count = len(re.findall(r'&&|\|\|', code))
        metrics['cyclomatic_complexity'] = 1 + if_count + case_count + ternary_count + and_or_count
        
        # Boucles
        for_count = len(re.findall(r'\bfor\s*\(', code))
        while_count = len(re.findall(r'\bwhile\s*\(', code))
        do_count = len(re.findall(r'\bdo\s*{', code))
        
        metrics['for_loop_count'] = for_count
        metrics['while_loop_count'] = while_count
        metrics['total_loops'] = for_count + while_count + do_count
        
        # =====================================================================
        # MÉTRIQUES STRUCTURELLES (approximation CK)
        # =====================================================================
        
        # Nombre de classes
        class_count = len(re.findall(r'\bclass\s+\w+', code))
        interface_count = len(re.findall(r'\binterface\s+\w+', code))
        metrics['class_count'] = class_count
        metrics['interface_count'] = interface_count
        
        # Nombre de méthodes (approximation de WMC)
        method_pattern = r'(public|private|protected)?\s*(static)?\s*\w+\s+\w+\s*\([^)]*\)\s*{'
        method_count = len(re.findall(method_pattern, code))
        metrics['method_count'] = max(method_count, 1)
        
        # Attributs de classe
        field_pattern = r'(private|protected|public)\s+(static\s+)?(final\s+)?\w+\s+\w+\s*[;=]'
        field_count = len(re.findall(field_pattern, code))
        metrics['field_count'] = field_count
        
        # WMC approximé (somme des complexités des méthodes)
        metrics['wmc_approx'] = metrics['cyclomatic_complexity']
        
        # Imports (CBO - Coupling Between Objects approximé)
        import_count = len(re.findall(r'\bimport\s+[\w.]+;', code))
        metrics['import_count'] = import_count
        metrics['cbo_approx'] = import_count  # Couplage approximé par les imports
        
        # Héritage (DIT approximé)
        extends_count = len(re.findall(r'\bextends\s+\w+', code))
        implements_count = len(re.findall(r'\bimplements\s+[\w,\s]+', code))
        metrics['extends_count'] = extends_count
        metrics['implements_count'] = implements_count
        metrics['dit_approx'] = 1 + extends_count  # Profondeur minimale
        
        # =====================================================================
        # MÉTRIQUES DE QUALITÉ DE CODE
        # =====================================================================
        
        # Try-catch (gestion d'erreurs)
        try_count = len(re.findall(r'\btry\s*{', code))
        catch_count = len(re.findall(r'\bcatch\s*\(', code))
        finally_count = len(re.findall(r'\bfinally\s*{', code))
        metrics['try_count'] = try_count
        metrics['catch_count'] = catch_count
        metrics['error_handling_ratio'] = try_count / max(metrics['method_count'], 1)
        
        # Assertions et logs
        assert_count = len(re.findall(r'\bassert\s+', code))
        log_count = len(re.findall(r'\b(log|LOG|logger|LOGGER)\.\w+\(', code))
        metrics['assert_count'] = assert_count
        metrics['log_count'] = log_count
        
        # Retours (complexité des retours)
        return_count = len(re.findall(r'\breturn\b', code))
        metrics['return_count'] = return_count
        metrics['return_per_method'] = return_count / max(metrics['method_count'], 1)
        
        # =====================================================================
        # MÉTRIQUES DÉRIVÉES
        # =====================================================================
        
        # Densité de code
        metrics['code_density'] = sloc / max(metrics['loc'], 1)
        
        # Complexité par méthode
        metrics['complexity_per_method'] = metrics['cyclomatic_complexity'] / max(metrics['method_count'], 1)
        
        # Taille moyenne des méthodes
        metrics['avg_method_size'] = sloc / max(metrics['method_count'], 1)
        
        # Ratio fields/methods (cohésion approximée)
        metrics['field_method_ratio'] = field_count / max(metrics['method_count'], 1)
        
        # Longueur moyenne des lignes
        non_empty_lines = [l for l in lines if l.strip()]
        if non_empty_lines:
            metrics['avg_line_length'] = np.mean([len(l) for l in non_empty_lines])
            metrics['max_line_length'] = max(len(l) for l in non_empty_lines)
        else:
            metrics['avg_line_length'] = 0
            metrics['max_line_length'] = 0
        
        return metrics
    
    def get_feature_names_out(self, input_features=None):
        """Retourne les noms des features pour sklearn"""
        return self.feature_names


class TfidfCodeVectorizer(BaseEstimator, TransformerMixin):
    """
    FEATURE ENGINEERING: Vectorisation TF-IDF du code source
    
    POURQUOI C'EST NÉCESSAIRE:
    ─────────────────────────────────────────────────────────────────────────
    - Capture les patterns de code (noms de méthodes, imports fréquents)
    - Les mots-clés utilisés peuvent indiquer des zones à risque
    - Complément aux métriques structurelles
    
    QUAND L'APPLIQUER:
    ─────────────────────────────────────────────────────────────────────────
    ⚠️ APRÈS le split train/test (CRITIQUE!)
    - TF-IDF calcule des statistiques globales (IDF = fréquence inverse)
    - FIT uniquement sur TRAIN, TRANSFORM sur TRAIN et TEST
    - Sinon: DATA LEAKAGE car le test influence les poids IDF
    """
    
    def __init__(self, max_features: int = 500, ngram_range: Tuple = (1, 2)):
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.vectorizer = None
        
    def _preprocess_code(self, code: str) -> str:
        """Prétraitement du code pour TF-IDF"""
        # Supprimer les commentaires
        code = re.sub(r'//.*$', ' ', code, flags=re.MULTILINE)
        code = re.sub(r'/\*.*?\*/', ' ', code, flags=re.DOTALL)
        
        # Supprimer les strings literals
        code = re.sub(r'"[^"]*"', ' STRING ', code)
        code = re.sub(r"'[^']*'", ' CHAR ', code)
        
        # Supprimer les nombres
        code = re.sub(r'\b\d+\.?\d*\b', ' NUM ', code)
        
        # Splitter les camelCase en mots séparés
        code = re.sub(r'([a-z])([A-Z])', r'\1 \2', code)
        
        # Supprimer les caractères spéciaux (garder underscores)
        code = re.sub(r'[^a-zA-Z_\s]', ' ', code)
        
        # Minuscules et normalisation des espaces
        code = code.lower()
        code = ' '.join(code.split())
        
        return code
    
    def fit(self, X, y=None):
        """
        FIT sur les données d'entraînement UNIQUEMENT
        
        ⚠️ ATTENTION AU DATA LEAKAGE:
        - Cette méthode doit être appelée SEULEMENT sur X_train
        - Les statistiques IDF sont calculées ici
        """
        logger.info("Fitting TF-IDF vectorizer (TRAIN only)...")
        
        preprocessed = [self._preprocess_code(str(code)) for code in X]
        
        self.vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            ngram_range=self.ngram_range,
            min_df=2,  # Ignorer les termes trop rares
            max_df=0.95,  # Ignorer les termes trop fréquents
            stop_words='english',
            sublinear_tf=True  # Utiliser log(1 + tf)
        )
        
        self.vectorizer.fit(preprocessed)
        logger.info(f"TF-IDF vocabulary size: {len(self.vectorizer.vocabulary_)}")
        
        return self
    
    def transform(self, X) -> np.ndarray:
        """Transform les données en utilisant le vectorizer fitté"""
        preprocessed = [self._preprocess_code(str(code)) for code in X]
        return self.vectorizer.transform(preprocessed).toarray()
    
    def get_feature_names_out(self, input_features=None):
        """Retourne les noms des features TF-IDF"""
        if self.vectorizer:
            return [f"tfidf_{name}" for name in self.vectorizer.get_feature_names_out()]
        return []


# ============================================================================
# SECTION 4: NORMALISATION ET STANDARDISATION
# ============================================================================

class FeatureScaler:
    """
    ÉTAPE 2: NORMALISATION / STANDARDISATION DES VARIABLES NUMÉRIQUES
    
    POURQUOI C'EST NÉCESSAIRE:
    ─────────────────────────────────────────────────────────────────────────
    - Les features ont des échelles très différentes (LOC: 10-10000, CC: 1-50)
    - Beaucoup d'algorithmes ML sont sensibles à l'échelle (SVM, KNN, réseaux)
    - Améliore la convergence des optimiseurs (gradient descent)
    - Rend les coefficients interprétables (régression)
    
    QUAND L'APPLIQUER:
    ─────────────────────────────────────────────────────────────────────────
    ⚠️ APRÈS le split train/test (CRITIQUE!)
    - Les paramètres (mean, std, min, max) doivent être calculés sur TRAIN
    - FIT sur TRAIN uniquement
    - TRANSFORM sur TRAIN et TEST avec les mêmes paramètres
    
    TYPES DE SCALERS:
    ─────────────────────────────────────────────────────────────────────────
    1. StandardScaler (Z-score): X' = (X - μ) / σ
       - Quand: distribution normale, pas d'outliers extrêmes
       - Mean=0, Std=1
    
    2. MinMaxScaler: X' = (X - min) / (max - min)
       - Quand: bornes connues, pas d'outliers
       - Range [0, 1]
    
    3. RobustScaler: X' = (X - median) / IQR
       - Quand: présence d'outliers (notre cas!)
       - Utilise médiane et IQR, robuste aux outliers
    """
    
    def __init__(self, scaler_type: str = 'robust'):
        self.scaler_type = scaler_type
        self.scaler = None
        self.columns = None
        self.is_fitted = False
        
    def _create_scaler(self):
        """Crée le scaler approprié"""
        if self.scaler_type == 'standard':
            return StandardScaler()
        elif self.scaler_type == 'minmax':
            return MinMaxScaler()
        elif self.scaler_type == 'robust':
            return RobustScaler()
        else:
            raise ValueError(f"Scaler inconnu: {self.scaler_type}")
    
    def fit(self, X: pd.DataFrame, columns: List[str] = None):
        """
        FIT sur les données d'entraînement UNIQUEMENT
        
        ⚠️ ATTENTION AU DATA LEAKAGE:
        - Calcule mean/std/min/max sur X_train seulement
        - Ces statistiques ne doivent JAMAIS inclure le test set
        """
        logger.info(f"Fitting {self.scaler_type} scaler (TRAIN only)...")
        
        self.columns = columns or X.select_dtypes(include=[np.number]).columns.tolist()
        self.scaler = self._create_scaler()
        
        # FIT sur les colonnes numériques
        self.scaler.fit(X[self.columns])
        self.is_fitted = True
        
        logger.info(f"Scaler fitted sur {len(self.columns)} colonnes")
        return self
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform les données avec le scaler fitté"""
        if not self.is_fitted:
            raise RuntimeError("Scaler must be fitted before transform")
        
        X_copy = X.copy()
        X_copy[self.columns] = self.scaler.transform(X[self.columns])
        
        return X_copy
    
    def fit_transform(self, X: pd.DataFrame, columns: List[str] = None) -> pd.DataFrame:
        """Fit et transform (pour le train set uniquement)"""
        self.fit(X, columns)
        return self.transform(X)


# ============================================================================
# SECTION 5: ENCODAGE DES VARIABLES CATÉGORIELLES
# ============================================================================

class CategoricalEncoder:
    """
    ÉTAPE 3: ENCODAGE DES VARIABLES CATÉGORIELLES
    
    POURQUOI C'EST NÉCESSAIRE:
    ─────────────────────────────────────────────────────────────────────────
    - Les modèles ML ne peuvent pas traiter directement les strings
    - Le choix de l'encodage impacte les performances du modèle
    - Certains encodages créent des relations ordinales non souhaitées
    
    QUAND L'APPLIQUER:
    ─────────────────────────────────────────────────────────────────────────
    
    AVANT SPLIT (OK pour certains):
    ✅ LabelEncoder simple (cible binaire Bug: True/False -> 1/0)
    ✅ Mapping fixe prédéfini
    
    APRÈS SPLIT (obligatoire pour):
    ⚠️ OneHotEncoder (catégories inconnues dans test)
    ⚠️ TargetEncoder (utilise la target, risque de leakage!)
    ⚠️ FrequencyEncoder (statistiques globales)
    
    TYPES D'ENCODAGE:
    ─────────────────────────────────────────────────────────────────────────
    1. LabelEncoder: catégorie -> entier (0, 1, 2...)
       - Usage: variables ordinales, target binaire
       - ⚠️ Crée un ordre implicite
    
    2. OneHotEncoder: catégorie -> vecteur binaire
       - Usage: variables nominales (pas d'ordre)
       - ⚠️ Explosion dimensionnelle si haute cardinalité
    
    3. OrdinalEncoder: comme Label mais avec ordre explicite
       - Usage: tailles (S, M, L), niveaux (Low, Medium, High)
    
    4. TargetEncoder: catégorie -> moyenne de la target
       - Usage: haute cardinalité
       - ⚠️⚠️ TRÈS RISQUÉ pour le data leakage!
    """
    
    def __init__(self):
        self.encoders = {}
        self.is_fitted = False
        
    def fit(self, X: pd.DataFrame, y: pd.Series = None, 
            columns_config: Dict[str, str] = None):
        """
        FIT les encodeurs sur les données d'entraînement
        
        Args:
            X: DataFrame d'entraînement
            y: Variable cible (pour TargetEncoder)
            columns_config: Dict {colonne: type_encodage}
                           Types: 'label', 'onehot', 'ordinal', 'target'
        """
        logger.info("Fitting categorical encoders (TRAIN only)...")
        
        if columns_config is None:
            # Détection automatique des colonnes catégorielles
            columns_config = {}
            for col in X.select_dtypes(include=['object', 'category']).columns:
                n_unique = X[col].nunique()
                if n_unique == 2:
                    columns_config[col] = 'label'
                elif n_unique <= 10:
                    columns_config[col] = 'onehot'
                else:
                    columns_config[col] = 'label'  # Fallback
        
        for col, encoding_type in columns_config.items():
            if col not in X.columns:
                continue
                
            if encoding_type == 'label':
                encoder = LabelEncoder()
                encoder.fit(X[col].astype(str))
                self.encoders[col] = ('label', encoder)
                
            elif encoding_type == 'onehot':
                encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
                encoder.fit(X[[col]].astype(str))
                self.encoders[col] = ('onehot', encoder)
                
            elif encoding_type == 'ordinal':
                encoder = OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)
                encoder.fit(X[[col]].astype(str))
                self.encoders[col] = ('ordinal', encoder)
        
        self.is_fitted = True
        logger.info(f"Encoders fitted pour {len(self.encoders)} colonnes")
        return self
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform les colonnes catégorielles"""
        if not self.is_fitted:
            raise RuntimeError("Encoders must be fitted before transform")
        
        X_copy = X.copy()
        
        for col, (encoding_type, encoder) in self.encoders.items():
            if col not in X_copy.columns:
                continue
                
            if encoding_type == 'label':
                # Gérer les valeurs inconnues
                known_classes = set(encoder.classes_)
                X_copy[col] = X_copy[col].astype(str).apply(
                    lambda x: encoder.transform([x])[0] if x in known_classes else -1
                )
                
            elif encoding_type == 'onehot':
                encoded = encoder.transform(X_copy[[col]].astype(str))
                feature_names = [f"{col}_{cat}" for cat in encoder.categories_[0]]
                encoded_df = pd.DataFrame(encoded, columns=feature_names, index=X_copy.index)
                X_copy = pd.concat([X_copy.drop(columns=[col]), encoded_df], axis=1)
                
            elif encoding_type == 'ordinal':
                X_copy[col] = encoder.transform(X_copy[[col]].astype(str)).flatten()
        
        return X_copy


# ============================================================================
# SECTION 6: PIPELINE COMPLET ANTI-LEAKAGE
# ============================================================================

class MLFeatureEngineeringPipeline:
    
    def __init__(self, config: MLConfig = None):
        self.config = config or MLConfig()
        
        # Composants du pipeline
        self.schema_harmonizer = SchemaHarmonizer({
            'File': 'str',
            'Bug': 'bool',
            'SRC': 'str',
            '_project': 'category',
            '_version': 'str'
        })
        
        self.code_extractor = CodeMetricsExtractor()
        self.tfidf_vectorizer = TfidfCodeVectorizer(
            max_features=self.config.tfidf_max_features
        )
        self.scaler = FeatureScaler(scaler_type=self.config.scaler_type)
        self.encoder = CategoricalEncoder()
        
        # Données
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.feature_names = []
        
        # Setup
        os.makedirs(self.config.output_dir, exist_ok=True)
    
    def load_and_merge_data(self) -> pd.DataFrame:
        """
        Charge et fusionne tous les fichiers CSV
        
        ÉTAPE 1: Harmonisation avant split (SAFE)
        """
        logger.info("="*60)
        logger.info("ÉTAPE 1: CHARGEMENT ET HARMONISATION")
        logger.info("="*60)
        
        all_data = []
        
        for filename in os.listdir(self.config.input_dir):
            if not filename.endswith('.csv'):
                continue
            if filename in self.config.exclude_files:
                continue
            
            filepath = os.path.join(self.config.input_dir, filename)
            
            try:
                df = pd.read_csv(filepath, encoding='utf-8')
                
                if len(df) == 0:
                    logger.warning(f"Fichier vide ignoré: {filename}")
                    continue
                
                # Harmoniser le schéma
                df = self.schema_harmonizer.harmonize(df, filename)
                
                all_data.append(df)
                logger.info(f"  ✓ Chargé: {filename} ({len(df)} lignes)")
                
            except Exception as e:
                logger.error(f"  ✗ Erreur: {filename} - {e}")
        
        merged = pd.concat(all_data, ignore_index=True)
        logger.info(f"\nTotal: {len(merged)} enregistrements")
        
        return merged
    
    def extract_base_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extrait les features indépendantes (avant split - SAFE)
        
        ÉTAPE 2: Feature engineering sans statistiques globales
        """
        logger.info("="*60)
        logger.info("ÉTAPE 2: EXTRACTION FEATURES INDÉPENDANTES")
        logger.info("="*60)
        
        # Extraire les métriques de code (calcul par fichier, pas de stats globales)
        logger.info("Extraction des métriques de code...")
        code_metrics = self.code_extractor.transform(df[self.config.text_column])
        
        # Fusionner avec les données originales
        result = pd.concat([
            df.reset_index(drop=True),
            code_metrics.reset_index(drop=True)
        ], axis=1)
        
        logger.info(f"  ✓ {len(code_metrics.columns)} métriques de code extraites")
        
        return result
    
    def split_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Split train/test avec stratification
        
        STRATÉGIES DE SPLIT ANTI-LEAKAGE:
        ─────────────────────────────────────────────────────────────────────
        1. Stratification sur la target (Bug) - préserve la distribution
        2. Groupement par projet - évite le leakage inter-versions
        """
        logger.info("="*60)
        logger.info("ÉTAPE 3: SPLIT TRAIN/TEST")
        logger.info("="*60)
        
        # Séparer features et target
        y = df[self.config.target_column].astype(int)
        X = df.drop(columns=[self.config.target_column])
        
        # Option 1: Split simple stratifié
        if '_project' not in df.columns:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y,
                test_size=self.config.test_size,
                random_state=self.config.random_state,
                stratify=y if self.config.stratify else None
            )
        else:
            # Option 2: Split groupé par projet (meilleur pour éviter leakage)
            # Utiliser les dernières versions de chaque projet pour le test
            logger.info("Split groupé par projet (dernières versions -> test)")
            
            # Identifier les dernières versions par projet
            test_mask = df.groupby('_project')['_version'].transform(
                lambda x: x == x.max()
            )
            
            # Alternative: split aléatoire stratifié si les groupes sont trop petits
            if test_mask.sum() < len(df) * 0.1:
                logger.info("Groupes trop petits, fallback vers split stratifié")
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y,
                    test_size=self.config.test_size,
                    random_state=self.config.random_state,
                    stratify=y
                )
            else:
                X_test = X[test_mask]
                X_train = X[~test_mask]
                y_test = y[test_mask]
                y_train = y[~test_mask]
        
        logger.info(f"  Train: {len(X_train)} ({len(X_train)/len(X)*100:.1f}%)")
        logger.info(f"  Test:  {len(X_test)} ({len(X_test)/len(X)*100:.1f}%)")
        logger.info(f"  Target distribution (train): {y_train.mean()*100:.1f}% positifs")
        logger.info(f"  Target distribution (test):  {y_test.mean()*100:.1f}% positifs")
        
        return X_train, X_test, y_train, y_test
    
    def fit_transformers(self, X_train: pd.DataFrame, y_train: pd.Series):
        """
        FIT des transformateurs sur TRAIN uniquement
        
        ⚠️ CRITIQUE POUR ÉVITER LE DATA LEAKAGE
        - Tous les paramètres statistiques sont calculés ici
        - X_test ne doit JAMAIS être utilisé dans cette méthode
        """
        logger.info("="*60)
        logger.info("ÉTAPE 4: FIT TRANSFORMERS (TRAIN ONLY)")
        logger.info("="*60)
        
        # Identifier les colonnes numériques (exclure ID et texte)
        exclude_cols = [self.config.id_column, self.config.text_column] + \
                       self.config.metadata_columns
        numeric_cols = [c for c in X_train.select_dtypes(include=[np.number]).columns
                       if c not in exclude_cols]
        
        # 1. FIT TF-IDF sur le code source (TRAIN ONLY!)
        if self.config.use_tfidf and self.config.text_column in X_train.columns:
            self.tfidf_vectorizer.fit(X_train[self.config.text_column])
        
        # 2. FIT Scaler sur les métriques numériques (TRAIN ONLY!)
        if numeric_cols:
            self.scaler.fit(X_train, columns=numeric_cols)
        
        # 3. FIT Encoder sur les catégorielles (TRAIN ONLY!)
        cat_config = {
            '_project': 'onehot' if '_project' in X_train.columns else None
        }
        cat_config = {k: v for k, v in cat_config.items() if v is not None}
        if cat_config:
            self.encoder.fit(X_train, y_train, cat_config)
        
        logger.info("  ✓ Transformers fittés sur TRAIN uniquement")
    
    def transform_data(self, X: pd.DataFrame, is_train: bool = True) -> pd.DataFrame:
        """
        Transform les données avec les transformateurs fittés
        
        Appliqué de manière identique sur TRAIN et TEST
        """
        set_name = "TRAIN" if is_train else "TEST"
        logger.info(f"Transform {set_name}...")
        
        result_parts = []
        
        # 1. Métriques de code (déjà calculées en amont)
        exclude_cols = [self.config.id_column, self.config.text_column] + \
                       self.config.metadata_columns
        numeric_cols = [c for c in X.select_dtypes(include=[np.number]).columns
                       if c not in exclude_cols]
        
        if numeric_cols:
            numeric_data = self.scaler.transform(X[numeric_cols])
            result_parts.append(numeric_data)
        
        # 2. TF-IDF du code source
        if self.config.use_tfidf and self.config.text_column in X.columns:
            tfidf_features = self.tfidf_vectorizer.transform(X[self.config.text_column])
            tfidf_df = pd.DataFrame(
                tfidf_features,
                columns=self.tfidf_vectorizer.get_feature_names_out(),
                index=X.index
            )
            result_parts.append(tfidf_df)
        
        # 3. Variables catégorielles encodées
        if self.encoder.is_fitted:
            cat_cols = [c for c in self.encoder.encoders.keys() if c in X.columns]
            if cat_cols:
                encoded = self.encoder.transform(X[cat_cols])
                # Ne garder que les colonnes transformées
                new_cols = [c for c in encoded.columns if c not in cat_cols]
                if new_cols:
                    result_parts.append(encoded[new_cols])
        
        # Concaténer toutes les parties
        if result_parts:
            result = pd.concat(result_parts, axis=1)
        else:
            result = X[numeric_cols].copy()
        
        self.feature_names = list(result.columns)
        logger.info(f"  ✓ {len(result.columns)} features finales")
        
        return result
    
    def run(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Exécute le pipeline complet
        
        SÉQUENCE ANTI-DATA LEAKAGE:
        1. Charger et harmoniser (AVANT split) ✅
        2. Extraire features indépendantes (AVANT split) ✅
        3. Split train/test ✅
        4. FIT sur TRAIN uniquement ⚠️
        5. TRANSFORM train et test avec mêmes params ✅
        """
        logger.info("\n" + "="*70)
        logger.info("ML FEATURE ENGINEERING PIPELINE")
        logger.info("="*70 + "\n")
        
        # Étape 1 & 2: Avant split (safe)
        df = self.load_and_merge_data()
        df = self.extract_base_features(df)
        
        # Étape 3: Split
        X_train, X_test, y_train, y_test = self.split_data(df)
        
        # Étape 4: FIT sur train uniquement (critique!)
        self.fit_transformers(X_train, y_train)
        
        # Étape 5: Transform les deux sets
        logger.info("="*60)
        logger.info("ÉTAPE 5: TRANSFORM DATA")
        logger.info("="*60)
        
        X_train_transformed = self.transform_data(X_train, is_train=True)
        X_test_transformed = self.transform_data(X_test, is_train=False)
        
        # Sauvegarder
        self._save_results(X_train_transformed, X_test_transformed, y_train, y_test)
        
        self.X_train = X_train_transformed
        self.X_test = X_test_transformed
        self.y_train = y_train
        self.y_test = y_test
        
        logger.info("\n" + "="*70)
        logger.info("PIPELINE TERMINÉ AVEC SUCCÈS")
        logger.info("="*70)
        
        return X_train_transformed, X_test_transformed, y_train, y_test
    
    def _save_results(self, X_train, X_test, y_train, y_test):
        """Sauvegarde les données prêtes pour ML"""
        logger.info("Sauvegarde des données...")
        
        # Ajouter la target aux DataFrames pour sauvegarde
        train_df = X_train.copy()
        train_df['Bug'] = y_train.values
        
        test_df = X_test.copy()
        test_df['Bug'] = y_test.values
        
        train_df.to_csv(
            os.path.join(self.config.output_dir, 'train_features.csv'),
            index=False
        )
        test_df.to_csv(
            os.path.join(self.config.output_dir, 'test_features.csv'),
            index=False
        )
        
        # Sauvegarder les noms des features
        with open(os.path.join(self.config.output_dir, 'feature_names.txt'), 'w') as f:
            f.write('\n'.join(self.feature_names))
        
        logger.info(f"  ✓ Données sauvegardées dans: {self.config.output_dir}")


# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

def main():
    """Point d'entrée principal"""
    
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                    ML FEATURE ENGINEERING PIPELINE                        ║
    ║                                                                           ║
    ║  Ce pipeline applique les transformations dans le bon ordre pour          ║
    ║  éviter tout data leakage:                                                ║
    ║                                                                           ║
    ║  1. Harmonisation schéma      AVANT split  ✅ Safe                        ║
    ║  2. Features indépendantes    AVANT split  ✅ Safe                        ║
    ║  3. Train/Test split          ────────────────────                        ║
    ║  4. FIT transformers          TRAIN ONLY   ⚠️ Critique                    ║
    ║  5. TRANSFORM data            BOTH         ✅ Safe (mêmes params)         ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Configuration
    config = MLConfig(
        use_tfidf=True,
        tfidf_max_features=300,  # Réduire pour performance
        scaler_type='robust',
        test_size=0.2
    )
    
    # Exécution du pipeline
    pipeline = MLFeatureEngineeringPipeline(config)
    X_train, X_test, y_train, y_test = pipeline.run()
    
    # Résumé final
    print(f"""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                           RÉSUMÉ FINAL                                    ║
    ╠══════════════════════════════════════════════════════════════════════════╣
    ║  Features extraites:    {len(pipeline.feature_names):>6}                                         ║
    ║  Train samples:         {len(X_train):>6}                                         ║
    ║  Test samples:          {len(X_test):>6}                                         ║
    ║  Train positifs:        {y_train.sum():>6} ({y_train.mean()*100:.1f}%)                              ║
    ║  Test positifs:         {y_test.sum():>6} ({y_test.mean()*100:.1f}%)                              ║
    ╠══════════════════════════════════════════════════════════════════════════╣
    ║  Données sauvegardées:  {config.output_dir}      ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """)
    
    return pipeline


if __name__ == "__main__":
    pipeline = main()
