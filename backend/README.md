# ACE Project - Backend

## Architecture des Microservices

Le backend est composé de 5 microservices Python/FastAPI + infrastructure:

```
backend/
├── docker-compose.yml          # Orchestration des services
├── init-db.sql                 # Initialisation PostgreSQL
├── nginx.conf                  # Reverse proxy
├── .env.example                # Variables d'environnement
│
└── services/
    ├── collecte-depots/        # Port 8001 - API principale
    ├── pretraitement-features/ # Port 8002 - Génération de features
    ├── ml-service/             # Port 8003 - Entraînement ML
    ├── moteur-priorisation/    # Port 8004 - Optimisation OR-Tools
    └── analyse-statique/       # Port 8005 - Métriques CK/McCabe
```

## Services

### 1. Collecte-Depots (Port 8001)
- API principale du backend
- Gestion des repositories
- Collecte des commits et issues via GitHub API
- Proxy vers les services ML

**Endpoints:**
- `GET/POST /api/repos` - Liste/Création de repos
- `POST /api/repos/{id}/collect` - Collecte des données
- `GET /api/ml/best-model` - Meilleur modèle
- `POST /api/ml/trigger-pipeline/{id}` - Lance le pipeline ML complet

### 2. Prétraitement-Features (Port 8002)
- Génération des features pour le ML
- Support SMOTE pour équilibrage
- Split temporel pour validation

**Endpoints:**
- `POST /features/generate` - Génère les features
- `GET /features/schema` - Schéma des features
- `GET /datasets/{id}` - Info dataset
- `GET /datasets/{id}/data` - Données du dataset

### 3. ML-Service (Port 8003)
- Entraînement avec auto-tuning (Optuna)
- Support XGBoost, LightGBM, Random Forest
- Métriques effort-aware (Popt@20, Recall@Top20%)
- Intégration MLflow

**Endpoints:**
- `POST /train/auto` - Entraînement avec tuning
- `POST /predict` - Prédictions
- `GET /api/models/list` - Liste des modèles
- `GET /ml/explain/global/{id}` - Explications SHAP

### 4. Moteur-Priorisation (Port 8004)
- Optimisation avec OR-Tools
- Heuristiques effort-aware
- Comparaison avec autres heuristiques

**Endpoints:**
- `POST /prioritize` - Plan de tests priorisé
- `POST /compare-heuristics` - Comparaison d'heuristiques
- `GET /policies` - Politiques de priorisation

### 5. Analyse-Statique (Port 8005)
- Complexité cyclomatique (McCabe)
- Métriques CK (WMC, DIT, NOC, CBO, RFC, LCOM)
- Dépendances (fan-in/fan-out)
- Détection de code smells

**Endpoints:**
- `POST /analyze` - Analyse d'un repo
- `GET /metrics/{id}` - Métriques par repo
- `GET /smells/{id}` - Code smells
- `GET /summary/{id}` - Résumé

## Démarrage

### Avec Docker Compose (Recommandé)

```bash
cd backend
cp .env.example .env
docker-compose up -d
```

### Développement Local

```bash
# Démarrer PostgreSQL et Redis
docker-compose up -d postgres redis mlflow

# Installer les dépendances pour chaque service
cd services/collecte-depots
pip install -r requirements.txt
uvicorn main:app --reload --port 8001

# Répéter pour les autres services...
```

## URLs des Services

| Service | URL | Description |
|---------|-----|-------------|
| Collecte-Depots | http://localhost:8001 | API principale |
| Prétraitement | http://localhost:8002 | Features |
| ML Service | http://localhost:8003 | ML/Training |
| Priorisation | http://localhost:8004 | Optimisation |
| Analyse Statique | http://localhost:8005 | Métriques |
| MLflow UI | http://localhost:5000 | Tracking |
| Nginx Gateway | http://localhost:80 | Reverse proxy |

## Base de Données

PostgreSQL avec les tables principales:
- `repositories` - Repos Git
- `commits` - Historique des commits
- `files` - Fichiers modifiés
- `file_metrics` - Métriques de code
- `code_smells` - Problèmes détectés
- `datasets` - Datasets ML
- `models` - Modèles entraînés
- `predictions` - Prédictions
- `prioritization_runs` - Plans de tests

## Métriques Implémentées (Cahier de Charges)

✅ **Complexité cyclomatique (McCabe)**
✅ **Métriques CK**: WMC, DIT, NOC, CBO, RFC, LCOM
✅ **Dépendances**: Fan-in/Fan-out (in/out degree)
✅ **Code Smells**: Detection automatique
✅ **F1/PR-AUC/ROC-AUC**: Métriques de classification
✅ **Popt@20**: Métrique effort-aware
✅ **Recall@Top20%**: Classes/lignes à risque
✅ **OR-Tools**: Optimisation de la priorisation
✅ **MLflow**: Tracking des expériences
✅ **PostgreSQL**: Politiques et poids

## Exemple de Pipeline Complet

```bash
# 1. Créer un repo
curl -X POST http://localhost:8001/api/repos \
  -H "Content-Type: application/json" \
  -d '{"name": "my-project", "url": "https://github.com/owner/repo"}'

# 2. Collecter les données
curl -X POST http://localhost:8001/api/repos/1/collect

# 3. Générer les features
curl -X POST http://localhost:8002/features/generate \
  -H "Content-Type: application/json" \
  -d '{"repo_id": 1, "balancing_strategy": "smote"}'

# 4. Entraîner le modèle
curl -X POST http://localhost:8003/train/auto \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": 1, "repo_id": 1, "model_family": "ensemble"}'

# 5. Prioriser les tests
curl -X POST http://localhost:8004/prioritize \
  -H "Content-Type: application/json" \
  -d '{"repo_id": 1, "items": [...], "budget": 1000}'
```
