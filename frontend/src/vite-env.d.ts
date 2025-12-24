/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_BACKEND_URL?: string;
  readonly VITE_ML_SERVICE_URL?: string;
  readonly VITE_PRETRAITEMENT_URL?: string;
  readonly VITE_MOTEUR_PRIORISATION_URL?: string;
  readonly VITE_MLFLOW_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

