-- ============================================
-- ACE Project - Database Initialization Script
-- ============================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================
-- Repositories and Version Control
-- ============================================

CREATE TABLE IF NOT EXISTS repositories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(512) NOT NULL UNIQUE,
    provider VARCHAR(50) DEFAULT 'github',
    default_branch VARCHAR(100) DEFAULT 'main',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_collected_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS commits (
    id SERIAL PRIMARY KEY,
    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    sha VARCHAR(64) NOT NULL,
    message TEXT,
    author_name VARCHAR(255),
    author_email VARCHAR(255),
    committed_at TIMESTAMP,
    files_changed INTEGER DEFAULT 0,
    insertions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    is_bugfix BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(repo_id, sha)
);

CREATE TABLE IF NOT EXISTS files (
    id SERIAL PRIMARY KEY,
    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    commit_id INTEGER REFERENCES commits(id) ON DELETE CASCADE,
    filepath VARCHAR(1024) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    extension VARCHAR(50),
    language VARCHAR(50),
    lines_added INTEGER DEFAULT 0,
    lines_deleted INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'modified', -- added, modified, deleted
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS issues (
    id SERIAL PRIMARY KEY,
    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    issue_number INTEGER NOT NULL,
    title VARCHAR(512),
    body TEXT,
    state VARCHAR(20) DEFAULT 'open',
    is_bug BOOLEAN DEFAULT FALSE,
    labels JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP,
    closed_at TIMESTAMP,
    UNIQUE(repo_id, issue_number)
);

-- ============================================
-- Static Analysis Metrics
-- ============================================

CREATE TABLE IF NOT EXISTS file_metrics (
    id SERIAL PRIMARY KEY,
    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    commit_sha VARCHAR(64),
    filepath VARCHAR(1024) NOT NULL,
    
    -- Complexité cyclomatique (McCabe)
    cyclomatic_complexity FLOAT DEFAULT 0,
    max_cyclomatic_complexity FLOAT DEFAULT 0,
    avg_cyclomatic_complexity FLOAT DEFAULT 0,
    
    -- Métriques CK
    wmc FLOAT DEFAULT 0,      -- Weighted Methods per Class
    dit FLOAT DEFAULT 0,      -- Depth of Inheritance Tree
    noc FLOAT DEFAULT 0,      -- Number Of Children
    cbo FLOAT DEFAULT 0,      -- Coupling Between Objects
    rfc FLOAT DEFAULT 0,      -- Response For a Class
    lcom FLOAT DEFAULT 0,     -- Lack of Cohesion of Methods
    
    -- Dépendances
    fan_in INTEGER DEFAULT 0,     -- In-degree
    fan_out INTEGER DEFAULT 0,    -- Out-degree
    
    -- Métriques de taille
    loc INTEGER DEFAULT 0,        -- Lines of Code
    sloc INTEGER DEFAULT 0,       -- Source Lines of Code
    comments INTEGER DEFAULT 0,
    blank_lines INTEGER DEFAULT 0,
    
    -- Métriques additionnelles
    num_classes INTEGER DEFAULT 0,
    num_methods INTEGER DEFAULT 0,
    num_fields INTEGER DEFAULT 0,
    
    -- Code smells count
    code_smells_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(repo_id, filepath, commit_sha)
);

CREATE TABLE IF NOT EXISTS code_smells (
    id SERIAL PRIMARY KEY,
    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    metric_id INTEGER REFERENCES file_metrics(id) ON DELETE CASCADE,
    filepath VARCHAR(1024) NOT NULL,
    smell_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) DEFAULT 'medium', -- low, medium, high, critical
    line_start INTEGER,
    line_end INTEGER,
    message TEXT,
    rule_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS class_metrics (
    id SERIAL PRIMARY KEY,
    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    filepath VARCHAR(1024) NOT NULL,
    class_name VARCHAR(255) NOT NULL,
    
    -- Métriques CK par classe
    wmc FLOAT DEFAULT 0,
    dit FLOAT DEFAULT 0,
    noc FLOAT DEFAULT 0,
    cbo FLOAT DEFAULT 0,
    rfc FLOAT DEFAULT 0,
    lcom FLOAT DEFAULT 0,
    
    -- Autres métriques
    num_methods INTEGER DEFAULT 0,
    num_fields INTEGER DEFAULT 0,
    loc INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- ML Datasets and Features
-- ============================================

CREATE TABLE IF NOT EXISTS datasets (
    id SERIAL PRIMARY KEY,
    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    name VARCHAR(255),
    version VARCHAR(50),
    train_samples INTEGER DEFAULT 0,
    test_samples INTEGER DEFAULT 0,
    n_features INTEGER DEFAULT 0,
    feature_names JSONB DEFAULT '[]'::jsonb,
    balancing_strategy VARCHAR(50) DEFAULT 'none',
    temporal_split BOOLEAN DEFAULT FALSE,
    split_date TIMESTAMP,
    train_path VARCHAR(512),
    test_path VARCHAR(512),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feature_vectors (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER REFERENCES datasets(id) ON DELETE CASCADE,
    file_id INTEGER,
    filepath VARCHAR(1024),
    
    -- Features vector (JSONB for flexibility)
    features JSONB NOT NULL,
    
    -- Label
    is_buggy BOOLEAN DEFAULT FALSE,
    bug_count INTEGER DEFAULT 0,
    
    -- Metadata
    commit_sha VARCHAR(64),
    split_type VARCHAR(20) DEFAULT 'train', -- train, test, validation
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- ML Models and Predictions
-- ============================================

CREATE TABLE IF NOT EXISTS models (
    id SERIAL PRIMARY KEY,
    model_id VARCHAR(128) UNIQUE NOT NULL,
    repo_id INTEGER REFERENCES repositories(id) ON DELETE SET NULL,
    dataset_id INTEGER REFERENCES datasets(id) ON DELETE SET NULL,
    
    model_type VARCHAR(100) NOT NULL,
    model_family VARCHAR(50), -- xgb, lgbm, rf, logreg, ensemble
    
    -- Hyperparamètres
    hyperparameters JSONB DEFAULT '{}'::jsonb,
    
    -- Métriques
    accuracy FLOAT,
    precision_score FLOAT,
    recall FLOAT,
    f1_score FLOAT,
    roc_auc FLOAT,
    pr_auc FLOAT,
    
    -- Métriques effort-aware
    popt_20 FLOAT,           -- Popt@20
    recall_top_20 FLOAT,     -- Recall@Top20%
    
    -- Seuil optimal
    optimal_threshold FLOAT DEFAULT 0.5,
    
    -- Matrice de confusion
    confusion_matrix JSONB,
    
    -- MLflow
    mlflow_run_id VARCHAR(64),
    mlflow_experiment_id VARCHAR(64),
    
    -- Chemin du modèle
    model_path VARCHAR(512),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_best BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES models(id) ON DELETE CASCADE,
    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    
    file_id INTEGER,
    filepath VARCHAR(1024),
    
    prediction INTEGER DEFAULT 0,
    probability FLOAT DEFAULT 0,
    risk_score FLOAT DEFAULT 0,
    uncertainty FLOAT,
    
    -- SHAP values pour explainabilité
    shap_values JSONB,
    top_contributors JSONB,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Test Prioritization
-- ============================================

CREATE TABLE IF NOT EXISTS prioritization_policies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Poids pour la priorisation
    risk_weight FLOAT DEFAULT 1.0,
    criticite_weight FLOAT DEFAULT 0.5,
    effort_weight FLOAT DEFAULT 0.3,
    coverage_weight FLOAT DEFAULT 0.2,
    recency_weight FLOAT DEFAULT 0.2,
    
    -- Contraintes
    default_budget INTEGER DEFAULT 1000,
    max_items INTEGER,
    
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prioritization_runs (
    id SERIAL PRIMARY KEY,
    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    model_id INTEGER REFERENCES models(id) ON DELETE SET NULL,
    policy_id INTEGER REFERENCES prioritization_policies(id) ON DELETE SET NULL,
    
    -- Configuration
    budget INTEGER NOT NULL,
    weights JSONB DEFAULT '{}'::jsonb,
    sprint_context JSONB,
    
    -- Résultats
    items_total INTEGER DEFAULT 0,
    items_selected INTEGER DEFAULT 0,
    effort_total FLOAT DEFAULT 0,
    effort_selected FLOAT DEFAULT 0,
    
    -- Plan de priorisation (JSON)
    plan JSONB NOT NULL,
    
    -- Métriques d'efficacité
    coverage_gain FLOAT,
    defects_caught_ratio FLOAT,
    time_saved_ratio FLOAT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS test_items (
    id SERIAL PRIMARY KEY,
    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    run_id INTEGER REFERENCES prioritization_runs(id) ON DELETE CASCADE,
    
    item_id VARCHAR(255) NOT NULL,
    filepath VARCHAR(1024),
    module VARCHAR(255),
    
    risk FLOAT DEFAULT 0,
    effort FLOAT DEFAULT 0,
    criticite FLOAT DEFAULT 1.0,
    coverage_gap FLOAT DEFAULT 0,
    risk_confidence FLOAT DEFAULT 0.5,
    
    priority_score FLOAT DEFAULT 0,
    rank INTEGER,
    selected BOOLEAN DEFAULT FALSE,
    selection_reason VARCHAR(255),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Dashboard and Metrics History
-- ============================================

CREATE TABLE IF NOT EXISTS metrics_history (
    id SERIAL PRIMARY KEY,
    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    metric_type VARCHAR(100) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quality_scores (
    id SERIAL PRIMARY KEY,
    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    
    -- Scores globaux
    overall_score FLOAT DEFAULT 0,
    maintainability_score FLOAT DEFAULT 0,
    reliability_score FLOAT DEFAULT 0,
    security_score FLOAT DEFAULT 0,
    
    -- Statistiques
    total_files INTEGER DEFAULT 0,
    files_at_risk INTEGER DEFAULT 0,
    avg_complexity FLOAT DEFAULT 0,
    code_smells_total INTEGER DEFAULT 0,
    
    -- Tests
    test_pass_rate FLOAT DEFAULT 0,
    test_coverage FLOAT DEFAULT 0,
    
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Heuristics Comparison
-- ============================================

CREATE TABLE IF NOT EXISTS heuristic_baselines (
    id SERIAL PRIMARY KEY,
    repo_id INTEGER REFERENCES repositories(id) ON DELETE CASCADE,
    run_id INTEGER REFERENCES prioritization_runs(id) ON DELETE CASCADE,
    
    heuristic_type VARCHAR(50) NOT NULL, -- complexity_only, coverage_only, recency_only, random
    
    -- Résultats
    items_selected INTEGER DEFAULT 0,
    effort_selected FLOAT DEFAULT 0,
    defects_caught INTEGER DEFAULT 0,
    defects_total INTEGER DEFAULT 0,
    recall FLOAT DEFAULT 0,
    precision_score FLOAT DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Insert default prioritization policy
-- ============================================

INSERT INTO prioritization_policies (name, description, risk_weight, criticite_weight, is_default, is_active)
VALUES (
    'Default Policy',
    'Politique de priorisation par défaut basée sur le risque et la criticité',
    1.0,
    0.5,
    TRUE,
    TRUE
) ON CONFLICT DO NOTHING;

-- ============================================
-- Indexes for performance
-- ============================================

CREATE INDEX IF NOT EXISTS idx_commits_repo_id ON commits(repo_id);
CREATE INDEX IF NOT EXISTS idx_commits_sha ON commits(sha);
CREATE INDEX IF NOT EXISTS idx_commits_committed_at ON commits(committed_at);

CREATE INDEX IF NOT EXISTS idx_files_repo_id ON files(repo_id);
CREATE INDEX IF NOT EXISTS idx_files_filepath ON files(filepath);

CREATE INDEX IF NOT EXISTS idx_file_metrics_repo_id ON file_metrics(repo_id);
CREATE INDEX IF NOT EXISTS idx_file_metrics_filepath ON file_metrics(filepath);

CREATE INDEX IF NOT EXISTS idx_models_repo_id ON models(repo_id);
CREATE INDEX IF NOT EXISTS idx_models_model_id ON models(model_id);
CREATE INDEX IF NOT EXISTS idx_models_is_active ON models(is_active);

CREATE INDEX IF NOT EXISTS idx_predictions_model_id ON predictions(model_id);
CREATE INDEX IF NOT EXISTS idx_predictions_repo_id ON predictions(repo_id);

CREATE INDEX IF NOT EXISTS idx_prioritization_runs_repo_id ON prioritization_runs(repo_id);

CREATE INDEX IF NOT EXISTS idx_metrics_history_repo_id ON metrics_history(repo_id);
CREATE INDEX IF NOT EXISTS idx_metrics_history_recorded_at ON metrics_history(recorded_at);
