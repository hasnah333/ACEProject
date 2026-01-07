"""
================================================================================
PIPELINE DE NETTOYAGE DE DONNÉES - DATASET PROMISE
================================================================================
Expert: Data Engineering
Optimisé pour: Traitement de gros volumes avec mémoire limitée

Structure:
    1. Configuration et paramètres
    2. Classes de validation
    3. Fonctions de nettoyage par type
    4. Pipeline principal avec chunks
    5. Reporting et logging

Auteur: Data Engineering Pipeline
Date: 2026-01-05
================================================================================
"""

import pandas as pd
import numpy as np
import os
import logging
import hashlib
import json
from datetime import datetime
from typing import Generator, Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from pathlib import Path
import gc
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# 1. CONFIGURATION ET PARAMÈTRES
# ============================================================================

@dataclass
class PipelineConfig:
    """Configuration centralisée du pipeline de nettoyage"""
    
    # Chemins
    input_dir: str = r"c:\Users\Hasna\OneDrive\Desktop\data\promise"
    output_dir: str = r"c:\Users\Hasna\OneDrive\Desktop\data\cleaned"
    log_dir: str = r"c:\Users\Hasna\OneDrive\Desktop\data\logs"
    
    # Paramètres de traitement
    chunk_size: int = 1000  # Nombre de lignes par chunk
    encoding: str = 'utf-8'
    
    # Fichiers à exclure (vides identifiés dans l'analyse)
    exclude_files: List[str] = field(default_factory=lambda: [
        'ivy-1.0_ground-truth-files_dataset.csv',
        'ivy-1.1_ground-truth-files_dataset.csv',
        'ivy-1.2_ground-truth-files_dataset.csv'
    ])
    
    # Règles de nettoyage par colonne
    column_rules: Dict = field(default_factory=lambda: {
        'File': {
            'type': 'string',
            'required': True,
            'unique': True,
            'validators': ['not_empty', 'valid_path']
        },
        'Bug': {
            'type': 'boolean',
            'required': True,
            'allowed_values': [True, False, 'True', 'False', 'true', 'false', 1, 0]
        },
        'SRC': {
            'type': 'string',
            'required': True,
            'min_length': 50,  # Un fichier Java minimal
            'validators': ['not_empty', 'valid_java']
        }
    })
    
    # Seuils pour outliers
    outlier_method: str = 'iqr'  # 'iqr', 'zscore', 'percentile'
    outlier_threshold: float = 1.5  # Pour IQR
    zscore_threshold: float = 3.0  # Pour Z-score
    
    # Rapport
    generate_report: bool = True
    verbose: bool = True


# ============================================================================
# 2. CLASSES DE VALIDATION ET UTILITAIRES
# ============================================================================

class DataQualityReport:
    """Collecte et génère des rapports de qualité des données"""
    
    def __init__(self):
        self.stats = {
            'files_processed': 0,
            'files_skipped': 0,
            'total_rows_input': 0,
            'total_rows_output': 0,
            'rows_removed': 0,
            'duplicates_removed': 0,
            'nulls_handled': 0,
            'types_corrected': 0,
            'outliers_flagged': 0,
            'errors': [],
            'warnings': [],
            'by_file': {}
        }
        
    def add_file_stats(self, filename: str, stats: Dict):
        """Ajoute les statistiques d'un fichier"""
        self.stats['by_file'][filename] = stats
        self.stats['total_rows_input'] += stats.get('rows_input', 0)
        self.stats['total_rows_output'] += stats.get('rows_output', 0)
        self.stats['duplicates_removed'] += stats.get('duplicates', 0)
        self.stats['nulls_handled'] += stats.get('nulls', 0)
        
    def add_error(self, filename: str, error: str):
        """Enregistre une erreur"""
        self.stats['errors'].append({'file': filename, 'error': error})
        
    def add_warning(self, filename: str, warning: str):
        """Enregistre un avertissement"""
        self.stats['warnings'].append({'file': filename, 'warning': warning})
        
    def generate_report(self) -> str:
        """Génère le rapport final"""
        report = []
        report.append("=" * 80)
        report.append(" RAPPORT DE NETTOYAGE DES DONNÉES")
        report.append("=" * 80)
        report.append(f"\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"\nFichiers traités: {self.stats['files_processed']}")
        report.append(f"Fichiers ignorés: {self.stats['files_skipped']}")
        report.append(f"\nLignes en entrée: {self.stats['total_rows_input']:,}")
        report.append(f"Lignes en sortie: {self.stats['total_rows_output']:,}")
        report.append(f"Lignes supprimées: {self.stats['total_rows_input'] - self.stats['total_rows_output']:,}")
        report.append(f"\nDoublons supprimés: {self.stats['duplicates_removed']:,}")
        report.append(f"Valeurs nulles traitées: {self.stats['nulls_handled']:,}")
        
        if self.stats['errors']:
            report.append(f"\n⚠️  ERREURS ({len(self.stats['errors'])}):")
            for err in self.stats['errors'][:10]:
                report.append(f"   - {err['file']}: {err['error']}")
                
        if self.stats['warnings']:
            report.append(f"\n⚡ AVERTISSEMENTS ({len(self.stats['warnings'])}):")
            for warn in self.stats['warnings'][:10]:
                report.append(f"   - {warn['file']}: {warn['warning']}")
        
        report.append("\n" + "=" * 80)
        return "\n".join(report)


class DataValidator:
    """Validateurs de données réutilisables"""
    
    @staticmethod
    def not_empty(value: Any) -> bool:
        """Vérifie que la valeur n'est pas vide"""
        if pd.isna(value):
            return False
        if isinstance(value, str) and value.strip() == '':
            return False
        return True
    
    @staticmethod
    def valid_path(value: str) -> bool:
        """Vérifie que la valeur ressemble à un chemin de fichier Java"""
        if not isinstance(value, str):
            return False
        return value.endswith('.java') and '/' in value
    
    @staticmethod
    def valid_java(value: str) -> bool:
        """Vérifie que le code ressemble à du Java valide"""
        if not isinstance(value, str):
            return False
        # Vérifications basiques de structure Java
        java_keywords = ['class ', 'public ', 'private ', 'import ', 'package ']
        return any(kw in value for kw in java_keywords)
    
    @staticmethod
    def is_boolean(value: Any) -> bool:
        """Vérifie si la valeur peut être convertie en booléen"""
        if isinstance(value, bool):
            return True
        if isinstance(value, (int, float)) and value in [0, 1, 0.0, 1.0]:
            return True
        if isinstance(value, str) and value.lower() in ['true', 'false', '0', '1']:
            return True
        return False


# ============================================================================
# 3. FONCTIONS DE NETTOYAGE PAR TYPE
# ============================================================================

class DataCleaners:
    """Collection de fonctions de nettoyage"""
    
    @staticmethod
    def clean_boolean(series: pd.Series) -> pd.Series:
        """
        Nettoie et standardise une colonne booléenne
        
        Logique métier:
        - Convertit les variations de True/False en booléens Python
        - Gère les valeurs numériques (0/1)
        - Préserve les NaN pour traitement ultérieur
        """
        def to_bool(val):
            if pd.isna(val):
                return np.nan
            if isinstance(val, bool):
                return val
            if isinstance(val, (int, float)):
                return bool(val)
            if isinstance(val, str):
                return val.lower() in ['true', '1', 'yes', 'oui']
            return np.nan
        
        return series.apply(to_bool)
    
    @staticmethod
    def clean_string(series: pd.Series, strip: bool = True, 
                     lowercase: bool = False) -> pd.Series:
        """
        Nettoie une colonne de chaînes de caractères
        
        Logique métier:
        - Supprime les espaces superflus
        - Normalise l'encodage
        - Option de mise en minuscules
        """
        result = series.copy()
        
        # Convertir en string
        result = result.astype(str)
        
        # Remplacer 'nan' string par NaN réel
        result = result.replace('nan', np.nan)
        result = result.replace('None', np.nan)
        
        if strip:
            result = result.str.strip()
        
        if lowercase:
            result = result.str.lower()
        
        return result
    
    @staticmethod
    def clean_path(series: pd.Series) -> pd.Series:
        """
        Nettoie les chemins de fichiers
        
        Logique métier:
        - Normalise les séparateurs (/ au lieu de \)
        - Supprime les espaces
        - Vérifie l'extension .java
        """
        result = series.str.strip()
        result = result.str.replace('\\', '/', regex=False)
        result = result.str.replace('//', '/', regex=False)
        return result
    
    @staticmethod
    def clean_source_code(series: pd.Series) -> pd.Series:
        """
        Nettoie le code source Java
        
        Logique métier:
        - Préserve le formatage original (important pour l'analyse)
        - Normalise les fins de ligne
        - Supprime les caractères nuls
        """
        result = series.copy()
        
        # Normaliser les fins de ligne
        result = result.str.replace('\r\n', '\n', regex=False)
        result = result.str.replace('\r', '\n', regex=False)
        
        # Supprimer les caractères nuls
        result = result.str.replace('\x00', '', regex=False)
        
        return result


class OutlierHandler:
    """Gestion des valeurs aberrantes"""
    
    @staticmethod
    def detect_iqr(series: pd.Series, threshold: float = 1.5) -> pd.Series:
        """
        Détecte les outliers avec la méthode IQR
        
        Logique métier:
        - Q1 - threshold*IQR < valeur < Q3 + threshold*IQR
        - Retourne un masque booléen (True = outlier)
        """
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - threshold * IQR
        upper = Q3 + threshold * IQR
        return (series < lower) | (series > upper)
    
    @staticmethod
    def detect_zscore(series: pd.Series, threshold: float = 3.0) -> pd.Series:
        """
        Détecte les outliers avec Z-score
        
        Logique métier:
        - |Z-score| > threshold = outlier
        """
        mean = series.mean()
        std = series.std()
        if std == 0:
            return pd.Series([False] * len(series), index=series.index)
        zscore = (series - mean) / std
        return abs(zscore) > threshold
    
    @staticmethod
    def handle_outliers(series: pd.Series, method: str = 'flag',
                       threshold: float = 1.5) -> tuple:
        """
        Gère les outliers selon la méthode choisie
        
        Méthodes:
        - 'flag': Retourne un masque sans modifier
        - 'clip': Limite aux bornes IQR
        - 'remove': Marque pour suppression
        - 'winsorize': Remplace par les percentiles
        
        Returns: (series_modifiée, nombre_outliers)
        """
        outlier_mask = OutlierHandler.detect_iqr(series, threshold)
        n_outliers = outlier_mask.sum()
        
        if method == 'flag':
            return series, n_outliers
        
        elif method == 'clip':
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - threshold * IQR
            upper = Q3 + threshold * IQR
            return series.clip(lower=lower, upper=upper), n_outliers
        
        elif method == 'winsorize':
            lower_pct = series.quantile(0.05)
            upper_pct = series.quantile(0.95)
            result = series.copy()
            result[series < lower_pct] = lower_pct
            result[series > upper_pct] = upper_pct
            return result, n_outliers
        
        return series, n_outliers


# ============================================================================
# 4. PIPELINE PRINCIPAL AVEC CHUNKS
# ============================================================================

class DataCleaningPipeline:
    """
    Pipeline de nettoyage de données avec traitement par chunks
    
    Architecture:
    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │   Lecture   │ ──► │  Nettoyage  │ ──► │   Écriture  │
    │   Chunks    │     │  par Chunk  │     │   Chunks    │
    └─────────────┘     └─────────────┘     └─────────────┘
           │                   │                   │
           ▼                   ▼                   ▼
    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │   Logging   │ ◄── │  Validation │ ──► │   Rapport   │
    └─────────────┘     └─────────────┘     └─────────────┘
    """
    
    def __init__(self, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.report = DataQualityReport()
        self.validator = DataValidator()
        self.cleaners = DataCleaners()
        self._setup_logging()
        self._setup_directories()
        
    def _setup_logging(self):
        """Configure le système de logging"""
        os.makedirs(self.config.log_dir, exist_ok=True)
        log_file = os.path.join(
            self.config.log_dir, 
            f"cleaning_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def _setup_directories(self):
        """Crée les répertoires de sortie"""
        os.makedirs(self.config.output_dir, exist_ok=True)
        os.makedirs(self.config.log_dir, exist_ok=True)
        
    def get_files_to_process(self) -> List[str]:
        """Retourne la liste des fichiers à traiter"""
        all_files = [
            f for f in os.listdir(self.config.input_dir)
            if f.endswith('.csv') and f not in self.config.exclude_files
        ]
        self.logger.info(f"Fichiers à traiter: {len(all_files)}")
        return all_files
    
    def read_chunks(self, filepath: str) -> Generator[pd.DataFrame, None, None]:
        """
        Générateur de chunks pour lecture mémoire-efficace
        
        PSEUDOCODE:
        -----------------------------------------
        POUR chaque chunk de taille N:
            LIRE chunk depuis fichier CSV
            YIELD chunk au pipeline
            LIBÉRER mémoire du chunk précédent
        FIN POUR
        -----------------------------------------
        """
        try:
            for chunk in pd.read_csv(
                filepath,
                chunksize=self.config.chunk_size,
                encoding=self.config.encoding,
                low_memory=True,
                dtype={'File': str, 'Bug': object, 'SRC': str}
            ):
                yield chunk
                gc.collect()  # Libère la mémoire
        except Exception as e:
            self.logger.error(f"Erreur lecture: {filepath} - {e}")
            self.report.add_error(os.path.basename(filepath), str(e))
            
    def clean_chunk(self, chunk: pd.DataFrame, filename: str) -> pd.DataFrame:
        """
        Nettoie un chunk de données
        
        PSEUDOCODE:
        -----------------------------------------
        1. VALIDER structure (colonnes attendues)
        2. SUPPRIMER doublons
        3. NETTOYER chaque colonne selon son type:
           - File: normaliser chemins
           - Bug: convertir en booléen
           - SRC: normaliser code source
        4. TRAITER valeurs manquantes
        5. VALIDER intégrité des données
        6. RETOURNER chunk nettoyé
        -----------------------------------------
        """
        stats = {
            'rows_input': len(chunk),
            'duplicates': 0,
            'nulls': 0,
            'invalid': 0
        }
        
        # 1. Vérifier les colonnes
        expected_cols = ['File', 'Bug', 'SRC']
        if not all(col in chunk.columns for col in expected_cols):
            self.report.add_error(filename, "Colonnes manquantes")
            return pd.DataFrame()
        
        # 2. Supprimer les doublons basés sur 'File'
        n_before = len(chunk)
        chunk = chunk.drop_duplicates(subset=['File'], keep='first')
        stats['duplicates'] = n_before - len(chunk)
        
        # 3. Nettoyer la colonne File
        chunk['File'] = self.cleaners.clean_path(chunk['File'])
        
        # 4. Nettoyer et standardiser Bug
        chunk['Bug'] = self.cleaners.clean_boolean(chunk['Bug'])
        
        # Marquer les valeurs Bug invalides
        invalid_bug = chunk['Bug'].isna()
        if invalid_bug.sum() > 0:
            self.report.add_warning(
                filename, 
                f"{invalid_bug.sum()} valeurs Bug invalides"
            )
            stats['nulls'] += invalid_bug.sum()
        
        # 5. Nettoyer le code source
        chunk['SRC'] = self.cleaners.clean_source_code(chunk['SRC'])
        
        # 6. Valider le code source (longueur minimale)
        src_too_short = chunk['SRC'].str.len() < self.config.column_rules['SRC']['min_length']
        if src_too_short.sum() > 0:
            self.report.add_warning(
                filename,
                f"{src_too_short.sum()} fichiers avec code source trop court"
            )
        
        # 7. Supprimer les lignes avec valeurs critiques manquantes
        n_before = len(chunk)
        chunk = chunk.dropna(subset=['File', 'Bug'])  # SRC peut être vide mais rare
        stats['invalid'] = n_before - len(chunk)
        
        # 8. Ajouter métadonnées de traçabilité
        project_version = filename.replace('_ground-truth-files_dataset.csv', '')
        parts = project_version.split('-')
        chunk['_project'] = parts[0]
        chunk['_version'] = '-'.join(parts[1:]) if len(parts) > 1 else ''
        chunk['_source_file'] = filename
        
        stats['rows_output'] = len(chunk)
        return chunk
    
    def compute_hash(self, df: pd.DataFrame) -> str:
        """Calcule un hash pour vérification d'intégrité"""
        return hashlib.md5(
            pd.util.hash_pandas_object(df).values
        ).hexdigest()
    
    def process_file(self, filename: str) -> Dict:
        """
        Traite un fichier complet par chunks
        
        PSEUDOCODE:
        -----------------------------------------
        INITIALISER stats et output_chunks
        
        POUR chaque chunk dans fichier:
            chunk_nettoye = NETTOYER(chunk)
            SI chunk_nettoye non vide:
                AJOUTER à output_chunks
            LIBÉRER mémoire
        FIN POUR
        
        SI output_chunks non vide:
            CONCATENER output_chunks
            ÉCRIRE fichier nettoyé
        
        RETOURNER stats
        -----------------------------------------
        """
        self.logger.info(f"Traitement: {filename}")
        
        filepath = os.path.join(self.config.input_dir, filename)
        output_path = os.path.join(self.config.output_dir, filename)
        
        file_stats = {
            'rows_input': 0,
            'rows_output': 0,
            'duplicates': 0,
            'nulls': 0,
            'chunks_processed': 0
        }
        
        cleaned_chunks = []
        
        # Traitement par chunks
        for chunk_num, chunk in enumerate(self.read_chunks(filepath)):
            file_stats['chunks_processed'] += 1
            file_stats['rows_input'] += len(chunk)
            
            # Nettoyer le chunk
            cleaned = self.clean_chunk(chunk, filename)
            
            if len(cleaned) > 0:
                cleaned_chunks.append(cleaned)
                file_stats['rows_output'] += len(cleaned)
            
            # Logging périodique
            if chunk_num % 10 == 0:
                self.logger.debug(
                    f"  Chunk {chunk_num}: {len(chunk)} -> {len(cleaned)} lignes"
                )
            
            # Libérer mémoire
            del chunk
            gc.collect()
        
        # Écrire le résultat
        if cleaned_chunks:
            result_df = pd.concat(cleaned_chunks, ignore_index=True)
            
            # Supprimer les doublons globaux (entre chunks)
            n_before = len(result_df)
            result_df = result_df.drop_duplicates(subset=['File'], keep='first')
            file_stats['duplicates'] += n_before - len(result_df)
            file_stats['rows_output'] = len(result_df)
            
            # Sauvegarder
            result_df.to_csv(output_path, index=False, encoding='utf-8')
            
            # Libérer mémoire
            del result_df
            del cleaned_chunks
            gc.collect()
            
            self.logger.info(
                f"  ✓ {filename}: {file_stats['rows_input']} -> "
                f"{file_stats['rows_output']} lignes"
            )
        else:
            self.logger.warning(f"  ⚠ {filename}: Aucune donnée valide")
            file_stats['rows_output'] = 0
        
        self.report.add_file_stats(filename, file_stats)
        return file_stats
    
    def run(self) -> DataQualityReport:
        """
        Exécute le pipeline complet
        
        PSEUDOCODE:
        -----------------------------------------
        DÉBUT pipeline
        
        fichiers = LISTER fichiers CSV valides
        
        POUR chaque fichier:
            SI fichier dans exclusions:
                IGNORER fichier
                CONTINUER
            
            stats = TRAITER fichier
            COLLECTER stats
            INCRÉMENTER compteurs
        FIN POUR
        
        GÉNÉRER rapport final
        SAUVEGARDER rapport
        
        FIN pipeline
        -----------------------------------------
        """
        self.logger.info("=" * 60)
        self.logger.info("DÉMARRAGE DU PIPELINE DE NETTOYAGE")
        self.logger.info("=" * 60)
        
        start_time = datetime.now()
        
        files = self.get_files_to_process()
        
        for filename in files:
            if filename in self.config.exclude_files:
                self.logger.info(f"Ignoré (exclusion): {filename}")
                self.report.stats['files_skipped'] += 1
                continue
            
            try:
                self.process_file(filename)
                self.report.stats['files_processed'] += 1
            except Exception as e:
                self.logger.error(f"Erreur: {filename} - {e}")
                self.report.add_error(filename, str(e))
                self.report.stats['files_skipped'] += 1
        
        # Finalisation
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        self.logger.info("=" * 60)
        self.logger.info(f"PIPELINE TERMINÉ en {duration:.2f} secondes")
        self.logger.info("=" * 60)
        
        # Générer et sauvegarder le rapport
        if self.config.generate_report:
            report_text = self.report.generate_report()
            report_path = os.path.join(
                self.config.output_dir,
                f"cleaning_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            self.logger.info(f"Rapport sauvegardé: {report_path}")
            print(report_text)
        
        return self.report


# ============================================================================
# 5. FONCTIONS UTILITAIRES ET BONNES PRATIQUES
# ============================================================================

def optimize_dataframe_memory(df: pd.DataFrame) -> pd.DataFrame:
    """
    Optimise l'utilisation mémoire d'un DataFrame
    
    BONNES PRATIQUES:
    - Convertir int64 -> int32/int16 si possible
    - Convertir float64 -> float32 si précision suffisante
    - Convertir object -> category si cardinalité faible
    """
    for col in df.columns:
        col_type = df[col].dtype
        
        if col_type == 'int64':
            if df[col].min() >= -32768 and df[col].max() <= 32767:
                df[col] = df[col].astype('int16')
            elif df[col].min() >= -2147483648 and df[col].max() <= 2147483647:
                df[col] = df[col].astype('int32')
                
        elif col_type == 'float64':
            df[col] = df[col].astype('float32')
            
        elif col_type == 'object':
            num_unique = df[col].nunique()
            if num_unique / len(df) < 0.5:  # Moins de 50% de valeurs uniques
                df[col] = df[col].astype('category')
    
    return df


def validate_pipeline_output(input_dir: str, output_dir: str) -> Dict:
    """
    Valide que le pipeline a produit des résultats cohérents
    
    BONNES PRATIQUES:
    - Vérifier que tous les fichiers ont été traités
    - Comparer les comptages avant/après
    - Vérifier l'intégrité des données
    """
    validation = {
        'input_files': 0,
        'output_files': 0,
        'files_missing': [],
        'integrity_ok': True
    }
    
    input_files = set(f for f in os.listdir(input_dir) if f.endswith('.csv'))
    output_files = set(f for f in os.listdir(output_dir) if f.endswith('.csv'))
    
    validation['input_files'] = len(input_files)
    validation['output_files'] = len(output_files)
    validation['files_missing'] = list(input_files - output_files)
    
    return validation


# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    # Configuration personnalisée (optionnelle)
    config = PipelineConfig(
        chunk_size=500,  # Réduire si mémoire limitée
        verbose=True
    )
    
    # Exécution du pipeline
    pipeline = DataCleaningPipeline(config)
    report = pipeline.run()
    
    # Validation finale
    validation = validate_pipeline_output(
        config.input_dir,
        config.output_dir
    )
    
    print("\n--- VALIDATION ---")
    print(f"Fichiers en entrée: {validation['input_files']}")
    print(f"Fichiers en sortie: {validation['output_files']}")
    if validation['files_missing']:
        print(f"Fichiers manquants: {validation['files_missing']}")
    else:
        print("✓ Tous les fichiers ont été traités")
