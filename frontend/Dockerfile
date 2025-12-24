FROM node:18-alpine AS builder

WORKDIR /app

# Accepter les arguments de build pour les variables d'environnement
ARG VITE_BACKEND_URL=http://localhost:8001
ARG VITE_ML_SERVICE_URL=http://localhost:8003
ARG VITE_PRETRAITEMENT_URL=http://localhost:8002
ARG VITE_MOTEUR_PRIORISATION_URL=http://localhost:8004
ARG VITE_MLFLOW_URL=http://localhost:5000

# Définir comme variables d'environnement pour le build
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL
ENV VITE_ML_SERVICE_URL=$VITE_ML_SERVICE_URL
ENV VITE_PRETRAITEMENT_URL=$VITE_PRETRAITEMENT_URL
ENV VITE_MOTEUR_PRIORISATION_URL=$VITE_MOTEUR_PRIORISATION_URL
ENV VITE_MLFLOW_URL=$VITE_MLFLOW_URL

# Copier les fichiers de dépendances
COPY package*.json ./
RUN npm ci

# Copier le code source
COPY . .

# Build de l'application
RUN npm run build

# Stage de production
FROM nginx:alpine

# Copier les fichiers buildés
COPY --from=builder /app/dist /usr/share/nginx/html

# Copier la configuration nginx
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

