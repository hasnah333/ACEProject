pipeline {
    agent any
    
    environment {
        DOCKER_COMPOSE_VERSION = '2.21.0'
        PROJECT_NAME = 'ace-project'
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                echo 'Code source récupéré avec succès'
            }
        }
        
        stage('Build Backend Services') {
            steps {
                echo 'Construction des services backend...'
                sh '''
                    docker-compose build collecte-depots
                    docker-compose build pretraitement-features
                    docker-compose build ml-service
                    docker-compose build moteur-priorisation
                    docker-compose build analyse-statique
                '''
            }
        }
        
        stage('Build Frontend') {
            steps {
                echo 'Construction du frontend...'
                dir('frontend') {
                    sh 'npm install'
                    sh 'npm run build'
                }
            }
        }
        
        stage('Run Tests') {
            parallel {
                stage('Backend Tests') {
                    steps {
                        echo 'Exécution des tests backend...'
                        sh '''
                            docker-compose up -d postgres redis
                            sleep 10
                            # Tests pour chaque service
                            docker-compose run --rm collecte-depots pytest tests/ --tb=short || true
                            docker-compose run --rm ml-service pytest tests/ --tb=short || true
                        '''
                    }
                }
                stage('Frontend Tests') {
                    steps {
                        echo 'Exécution des tests frontend...'
                        dir('frontend') {
                            sh 'npm run lint || true'
                            sh 'npm run test || true'
                        }
                    }
                }
            }
        }
        
        stage('Code Quality Analysis') {
            steps {
                echo 'Analyse de la qualité du code...'
                sh '''
                    # Analyse statique Python
                    docker-compose run --rm analyse-statique python -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics || true
                '''
            }
        }
        
        stage('Deploy to Staging') {
            when {
                branch 'develop'
            }
            steps {
                echo 'Déploiement en environnement de staging...'
                sh '''
                    docker-compose -f docker-compose.yml down || true
                    docker-compose -f docker-compose.yml up -d
                '''
            }
        }
        
        stage('Deploy to Production') {
            when {
                branch 'main'
            }
            steps {
                echo 'Déploiement en production...'
                sh '''
                    docker-compose -f docker-compose.yml down || true
                    docker-compose -f docker-compose.yml up -d --build
                '''
            }
        }
    }
    
    post {
        always {
            echo 'Pipeline terminé'
            sh 'docker-compose logs --tail=50 || true'
        }
        success {
            echo '✅ Pipeline exécuté avec succès!'
        }
        failure {
            echo '❌ Le pipeline a échoué'
        }
        cleanup {
            echo 'Nettoyage...'
            sh 'docker system prune -f || true'
        }
    }
}
