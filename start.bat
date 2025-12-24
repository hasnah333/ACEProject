@echo off
REM =============================================
REM ACE Project - Script de démarrage Windows
REM =============================================

echo.
echo ========================================
echo   ACE Project - Demarrage des services
echo ========================================
echo.

REM Vérifier si Docker est installé
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERREUR] Docker n'est pas installe ou n'est pas dans le PATH
    echo Veuillez installer Docker Desktop: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM Vérifier si Docker est en cours d'exécution
docker info >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERREUR] Docker n'est pas en cours d'execution
    echo Veuillez demarrer Docker Desktop
    pause
    exit /b 1
)

echo [INFO] Docker est disponible
echo.

REM Option de démarrage
echo Choisissez le mode de demarrage:
echo   1. Tout demarrer (Docker Compose)
echo   2. Backend uniquement (Docker)
echo   3. Frontend en mode developpement (npm)
echo   4. Tout arreter
echo.
set /p choice="Votre choix (1-4): "

if "%choice%"=="1" goto start_all
if "%choice%"=="2" goto start_backend
if "%choice%"=="3" goto start_frontend_dev
if "%choice%"=="4" goto stop_all
goto invalid

:start_all
echo.
echo [INFO] Demarrage de tous les services...
docker-compose up -d --build
echo.
echo [OK] Services demarres!
echo.
echo URLs des services:
echo   - Frontend:         http://localhost:3000
echo   - Backend API:      http://localhost:8001
echo   - ML Service:       http://localhost:8003
echo   - Pretraitement:    http://localhost:8002
echo   - Priorisation:     http://localhost:8004
echo   - Analyse Statique: http://localhost:8005
echo   - MLflow UI:        http://localhost:5000
echo.
goto end

:start_backend
echo.
echo [INFO] Demarrage du backend uniquement...
cd backend
docker-compose up -d --build
cd ..
echo.
echo [OK] Backend demarre!
echo.
goto end

:start_frontend_dev
echo.
echo [INFO] Demarrage du frontend en mode developpement...
cd frontend
echo [INFO] Installation des dependances...
call npm install
echo [INFO] Demarrage du serveur de developpement...
start cmd /k "npm run dev"
cd ..
echo.
echo [OK] Frontend demarre sur http://localhost:5173
echo.
goto end

:stop_all
echo.
echo [INFO] Arret de tous les services...
docker-compose down
cd backend
docker-compose down
cd ..
echo.
echo [OK] Tous les services sont arretes
echo.
goto end

:invalid
echo.
echo [ERREUR] Choix invalide
echo.

:end
pause
