export const API_CONFIG = {
  // Services backend
  BACKEND_URL: import.meta.env.VITE_BACKEND_URL || 'http://localhost:8001',
  ML_SERVICE_URL: import.meta.env.VITE_ML_SERVICE_URL || 'http://localhost:8003',
  PRETRAITEMENT_URL: import.meta.env.VITE_PRETRAITEMENT_URL || 'http://localhost:8002',
  MOTEUR_PRIORISATION_URL: import.meta.env.VITE_MOTEUR_PRIORISATION_URL || 'http://localhost:8004',
  ANALYSE_STATIQUE_URL: import.meta.env.VITE_ANALYSE_STATIQUE_URL || 'http://localhost:8005',

  // Services infrastructure
  MLFLOW_URL: import.meta.env.VITE_MLFLOW_URL || 'http://localhost:5000',
};

export default API_CONFIG;


