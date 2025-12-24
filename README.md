# ACE Project - Prédiction de Défauts et Priorisation de Tests

##  Description

Système intelligent de prédiction de défauts logiciels et de priorisation des tests basé sur :
- **Analyse statique** : Métriques CK (WMC, DIT, NOC, CBO, RFC, LCOM), complexité cyclomatique (McCabe)
- **Machine Learning** : Classification avec XGBoost/LightGBM, métriques effort-aware (Popt@20)
- **Optimisation** : OR-Tools pour la priorisation sous contraintes

##  Architecture

```
ACEProjet/
├── frontend/                    # React + TypeScript + Vite
│   ├── src/
│   │   ├── components/         # Composants UI
│   │   ├── pages/              # Pages de l'application
│   │   ├── services/api/       # Clients API
│   │   └── config/             # Configuration
│   └── ...
│
├── backend/                     # Python + FastAPI (Microservices)
│   ├── services/
│   │   ├── collecte-depots/    # Port 8001 - API principale
│   │   ├── pretraitement-features/  # Port 8002 - Features ML
│   │   ├── ml-service/         # Port 8003 - Entraînement ML
│   │   ├── moteur-priorisation/    # Port 8004 - OR-Tools
│   │   └── analyse-statique/   # Port 8005 - Métriques code
│   └── ...
│
└── docker-compose.yml          # Orchestration globale
```


##  Fonctionnalités

### Dashboard
- Vue d'ensemble de la qualité du code
- Métriques en temps réel
- Historique des runs MLflow

### Pipeline ML
1. **Collecte** : Récupération des commits et issues depuis GitHub
2. **Features** : Génération des features avec balancement SMOTE
3. **Entraînement** : Auto-tuning avec Optuna, tracking MLflow
4. **Priorisation** : Optimisation OR-Tools effort-aware

### Métriques Implémentées

| Catégorie | Métriques |
|-----------|-----------|
| **CK Metrics** | WMC, DIT, NOC, CBO, RFC, LCOM |
| **Complexité** | Cyclomatic (McCabe) |
| **Dépendances** | Fan-in, Fan-out |
| **ML** | F1, PR-AUC, ROC-AUC, Popt@20, Recall@Top20% |

##  URLs des Services

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | Interface utilisateur |
| Frontend Dev | http://localhost:5173 | Mode développement |
| Backend API | http://localhost:8001 | API principale |
| Prétraitement | http://localhost:8002 | Génération features |
| ML Service | http://localhost:8003 | Entraînement/Prédiction |
| Priorisation | http://localhost:8004 | Optimisation tests |
| Analyse Statique | http://localhost:8005 | Métriques code |
| MLflow | http://localhost:5000 | Tracking ML |
| PostgreSQL | localhost:5432 | Base de données |

##  API Endpoints Principaux

### Repositories
```
GET    /api/repos              # Liste des repos
POST   /api/repos              # Créer un repo
POST   /api/repos/{id}/collect # Collecter les données
```

### ML Pipeline
```
POST   /features/generate      # Générer les features
POST   /train/auto             # Entraîner avec auto-tuning
POST   /predict                # Prédictions
GET    /api/models/list        # Liste des modèles
```

### Priorisation
```
POST   /prioritize             # Plan de tests priorisé
GET    /policies               # Politiques de priorisation
```

##  Technologies

### Frontend
- React 18 + TypeScript
- Vite
- TailwindCSS
- Recharts (graphiques)

### Backend
- Python 3.11 + FastAPI
- SQLAlchemy (async)
- PostgreSQL
- Redis

### ML/AI
- Scikit-learn
- XGBoost / LightGBM
- Optuna (hyperparameter tuning)
- SHAP (explainability)
- MLflow (tracking)

### Optimisation
- OR-Tools (Google)

### Infrastructure
- Docker + Docker Compose
- Nginx
- PostgreSQL

## 📝 Cahier de Charges Implémenté

✅ Complexité cyclomatique (McCabe)
✅ Métriques CK (WMC, DIT, NOC, CBO, RFC, LCOM)
✅ Dépendances (in/out degree)
✅ Code smells
✅ F1/PR-AUC/ROC-AUC
✅ Popt@20 (effort-aware)
✅ Recall@Top20%
✅ OR-Tools optimisation
✅ MLflow intégration
✅ PostgreSQL (politiques/poids)
✅ Dashboard interactif

## 👥 Équipe

- othmani hasna
- ait ben brahim hasna
- ait bihi oumaima
- el bahtari hafsa

##  Ce projet est développé dans le cadre académique.
