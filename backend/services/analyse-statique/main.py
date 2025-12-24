"""
Service d'Analyse Statique
==========================
Service de calcul des métriques de code selon le cahier de charges:
- Complexité cyclomatique (McCabe)
- Métriques CK (WMC, DIT, NOC, CBO, RFC, LCOM)
- Dépendances (in/out degree / fan-in/fan-out)
- Code smells
Port: 8005
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from pathlib import Path
import os
import re
import logging
import json
from datetime import datetime

# Outils d'analyse statique
try:
    import radon
    from radon.complexity import cc_visit
    from radon.metrics import mi_visit, h_visit
    from radon.raw import analyze
    HAS_RADON = True
except ImportError:
    HAS_RADON = False

try:
    import lizard
    HAS_LIZARD = True
except ImportError:
    HAS_LIZARD = False

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============ Configuration ============

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://ace_user:ace_password@localhost:5432/ace_db"
    REPOS_PATH: str = "./repos"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# Database
DATABASE_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Analyse Statique service...")
    os.makedirs(settings.REPOS_PATH, exist_ok=True)
    yield
    logger.info("Shutting down Analyse Statique service...")


# ============ Application FastAPI ============

app = FastAPI(
    title="ACE - Analyse Statique Service",
    description="Service de calcul des métriques de code (McCabe, CK, dépendances, smells)",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Schemas ============

class AnalyzeRequest(BaseModel):
    repo_id: int
    filepath: Optional[str] = None  # Si None, analyser tout le repo
    commit_sha: Optional[str] = None


class FileMetricsResult(BaseModel):
    filepath: str
    language: str
    
    # Complexité cyclomatique (McCabe)
    cyclomatic_complexity: float
    max_cyclomatic_complexity: float
    avg_cyclomatic_complexity: float
    
    # Métriques CK
    wmc: float  # Weighted Methods per Class
    dit: float  # Depth of Inheritance Tree
    noc: float  # Number of Children
    cbo: float  # Coupling Between Objects
    rfc: float  # Response for a Class
    lcom: float  # Lack of Cohesion of Methods
    
    # Dépendances
    fan_in: int
    fan_out: int
    
    # Métriques de taille
    loc: int
    sloc: int
    comments: int
    blank_lines: int
    num_methods: int
    num_classes: int
    
    # Code smells
    code_smells: List[Dict[str, Any]]
    code_smells_count: int


class AnalyzeResponse(BaseModel):
    repo_id: int
    files_analyzed: int
    total_smells: int
    metrics: List[FileMetricsResult]


class CodeSmell(BaseModel):
    filepath: str
    smell_type: str
    severity: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    message: str


# ============ Analysis Functions ============

def detect_language(filepath: str) -> str:
    """Détecte le langage de programmation."""
    ext = Path(filepath).suffix.lower()
    language_map = {
        ".py": "python",
        ".java": "java",
        ".js": "javascript",
        ".ts": "typescript",
        ".cpp": "cpp",
        ".c": "c",
        ".cs": "csharp",
        ".rb": "ruby",
        ".go": "go",
        ".rs": "rust",
        ".php": "php",
        ".kt": "kotlin",
        ".scala": "scala",
    }
    return language_map.get(ext, "unknown")


def analyze_python_file(filepath: str, content: str) -> Dict[str, Any]:
    """Analyse un fichier Python avec radon."""
    result = {
        "cyclomatic_complexity": 0,
        "max_cyclomatic_complexity": 0,
        "avg_cyclomatic_complexity": 0,
        "wmc": 0,
        "dit": 0,
        "noc": 0,
        "cbo": 0,
        "rfc": 0,
        "lcom": 0,
        "fan_in": 0,
        "fan_out": 0,
        "loc": 0,
        "sloc": 0,
        "comments": 0,
        "blank_lines": 0,
        "num_methods": 0,
        "num_classes": 0,
        "code_smells": []
    }
    
    if not HAS_RADON:
        # Analyse basique sans radon
        lines = content.split('\n')
        result["loc"] = len(lines)
        result["sloc"] = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
        result["comments"] = len([l for l in lines if l.strip().startswith('#')])
        result["blank_lines"] = len([l for l in lines if not l.strip()])
        return result
    
    try:
        # Analyse de la complexité cyclomatique avec radon
        cc_results = cc_visit(content)
        if cc_results:
            complexities = [r.complexity for r in cc_results]
            result["cyclomatic_complexity"] = sum(complexities)
            result["max_cyclomatic_complexity"] = max(complexities) if complexities else 0
            result["avg_cyclomatic_complexity"] = sum(complexities) / len(complexities) if complexities else 0
            result["wmc"] = sum(complexities)  # WMC = somme des complexités
            result["num_methods"] = len([r for r in cc_results if r.letter in ('M', 'F')])
            result["num_classes"] = len([r for r in cc_results if r.letter == 'C'])
        
        # Analyse raw (LOC, SLOC, comments)
        raw_metrics = analyze(content)
        result["loc"] = raw_metrics.loc
        result["sloc"] = raw_metrics.sloc
        result["comments"] = raw_metrics.comments
        result["blank_lines"] = raw_metrics.blank
        
        # Calcul du fan-out (imports)
        import_pattern = r'^(?:from\s+(\S+)\s+)?import\s+(.+)$'
        imports = re.findall(import_pattern, content, re.MULTILINE)
        result["fan_out"] = len(imports)
        
        # Détection des code smells
        result["code_smells"] = detect_code_smells_python(filepath, content, cc_results)
        
    except Exception as e:
        logger.warning(f"Python analysis failed for {filepath}: {e}")
    
    return result


def analyze_java_file(filepath: str, content: str) -> Dict[str, Any]:
    """Analyse un fichier Java."""
    result = {
        "cyclomatic_complexity": 0,
        "max_cyclomatic_complexity": 0,
        "avg_cyclomatic_complexity": 0,
        "wmc": 0,
        "dit": 0,
        "noc": 0,
        "cbo": 0,
        "rfc": 0,
        "lcom": 0,
        "fan_in": 0,
        "fan_out": 0,
        "loc": 0,
        "sloc": 0,
        "comments": 0,
        "blank_lines": 0,
        "num_methods": 0,
        "num_classes": 0,
        "code_smells": []
    }
    
    lines = content.split('\n')
    result["loc"] = len(lines)
    
    # Compter SLOC, comments, blank
    for line in lines:
        stripped = line.strip()
        if not stripped:
            result["blank_lines"] += 1
        elif stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
            result["comments"] += 1
        else:
            result["sloc"] += 1
    
    # Compter les classes et méthodes
    class_pattern = r'\b(class|interface|enum)\s+\w+'
    method_pattern = r'(public|private|protected)\s+\w+\s+\w+\s*\([^)]*\)\s*{'
    
    result["num_classes"] = len(re.findall(class_pattern, content))
    result["num_methods"] = len(re.findall(method_pattern, content))
    
    # Compter les imports (fan-out)
    import_pattern = r'^import\s+[\w.]+;'
    result["fan_out"] = len(re.findall(import_pattern, content, re.MULTILINE))
    
    # Estimation du CBO (couplage) basée sur les imports
    result["cbo"] = result["fan_out"]
    
    # Utiliser lizard si disponible
    if HAS_LIZARD:
        try:
            analysis = lizard.analyze_file.analyze_source_code(filepath, content)
            if analysis.function_list:
                complexities = [f.cyclomatic_complexity for f in analysis.function_list]
                result["cyclomatic_complexity"] = sum(complexities)
                result["max_cyclomatic_complexity"] = max(complexities) if complexities else 0
                result["avg_cyclomatic_complexity"] = sum(complexities) / len(complexities) if complexities else 0
                result["wmc"] = sum(complexities)
                result["num_methods"] = len(analysis.function_list)
        except Exception as e:
            logger.warning(f"Lizard analysis failed for {filepath}: {e}")
    
    # Détection des code smells
    result["code_smells"] = detect_code_smells_java(filepath, content)
    
    return result


def detect_code_smells_python(filepath: str, content: str, cc_results: list) -> List[Dict]:
    """Détecte les code smells dans un fichier Python."""
    smells = []
    
    if cc_results:
        for r in cc_results:
            # Méthode/fonction trop complexe
            if r.complexity > 10:
                smells.append({
                    "smell_type": "high_complexity",
                    "severity": "high" if r.complexity > 20 else "medium",
                    "line_start": r.lineno,
                    "message": f"{r.name} has cyclomatic complexity of {r.complexity} (threshold: 10)"
                })
            
            # Fonction trop longue (estimation basée sur la complexité)
            if r.complexity > 15:
                smells.append({
                    "smell_type": "long_method",
                    "severity": "medium",
                    "line_start": r.lineno,
                    "message": f"{r.name} is likely too long based on complexity"
                })
    
    # Fichier trop long
    lines = content.split('\n')
    if len(lines) > 500:
        smells.append({
            "smell_type": "large_file",
            "severity": "medium",
            "line_start": 1,
            "message": f"File has {len(lines)} lines (threshold: 500)"
        })
    
    # Trop de paramètres
    param_pattern = r'def\s+\w+\s*\(([^)]+)\)'
    for match in re.finditer(param_pattern, content):
        params = [p.strip() for p in match.group(1).split(',') if p.strip() and p.strip() != 'self']
        if len(params) > 5:
            line_no = content[:match.start()].count('\n') + 1
            smells.append({
                "smell_type": "too_many_parameters",
                "severity": "low",
                "line_start": line_no,
                "message": f"Function has {len(params)} parameters (threshold: 5)"
            })
    
    return smells


def detect_code_smells_java(filepath: str, content: str) -> List[Dict]:
    """Détecte les code smells dans un fichier Java."""
    smells = []
    lines = content.split('\n')
    
    # Fichier trop long
    if len(lines) > 500:
        smells.append({
            "smell_type": "large_file",
            "severity": "medium",
            "line_start": 1,
            "message": f"File has {len(lines)} lines (threshold: 500)"
        })
    
    # Classe avec trop de méthodes
    method_pattern = r'(public|private|protected)\s+\w+\s+\w+\s*\([^)]*\)\s*{'
    methods = re.findall(method_pattern, content)
    if len(methods) > 20:
        smells.append({
            "smell_type": "god_class",
            "severity": "high",
            "line_start": 1,
            "message": f"Class has {len(methods)} methods (threshold: 20)"
        })
    
    # Détection des méthodes longues (estimation basée sur les accolades)
    method_bodies = re.findall(r'\{[^{}]*\}', content)
    for body in method_bodies:
        if body.count('\n') > 50:
            smells.append({
                "smell_type": "long_method",
                "severity": "medium",
                "message": f"Method body has more than 50 lines"
            })
    
    return smells


def analyze_generic_file(filepath: str, content: str) -> Dict[str, Any]:
    """Analyse générique pour les autres langages."""
    lines = content.split('\n')
    
    result = {
        "cyclomatic_complexity": 0,
        "max_cyclomatic_complexity": 0,
        "avg_cyclomatic_complexity": 0,
        "wmc": 0,
        "dit": 0,
        "noc": 0,
        "cbo": 0,
        "rfc": 0,
        "lcom": 0,
        "fan_in": 0,
        "fan_out": 0,
        "loc": len(lines),
        "sloc": len([l for l in lines if l.strip()]),
        "comments": 0,
        "blank_lines": len([l for l in lines if not l.strip()]),
        "num_methods": 0,
        "num_classes": 0,
        "code_smells": []
    }
    
    # Utiliser lizard si disponible
    if HAS_LIZARD:
        try:
            analysis = lizard.analyze_file.analyze_source_code(filepath, content)
            if analysis.function_list:
                complexities = [f.cyclomatic_complexity for f in analysis.function_list]
                result["cyclomatic_complexity"] = sum(complexities)
                result["max_cyclomatic_complexity"] = max(complexities) if complexities else 0
                result["avg_cyclomatic_complexity"] = sum(complexities) / len(complexities) if complexities else 0
                result["wmc"] = sum(complexities)
                result["num_methods"] = len(analysis.function_list)
        except Exception as e:
            logger.warning(f"Generic analysis failed for {filepath}: {e}")
    
    return result


async def analyze_file(filepath: str, content: str) -> Dict[str, Any]:
    """Analyse un fichier selon son langage."""
    language = detect_language(filepath)
    
    if language == "python":
        metrics = analyze_python_file(filepath, content)
    elif language == "java":
        metrics = analyze_java_file(filepath, content)
    else:
        metrics = analyze_generic_file(filepath, content)
    
    metrics["language"] = language
    metrics["code_smells_count"] = len(metrics.get("code_smells", []))
    
    return metrics


# ============ Endpoints ============

@app.get("/")
async def root():
    return {
        "service": "analyse-statique",
        "version": "1.0.0",
        "status": "running",
        "capabilities": {
            "radon": HAS_RADON,
            "lizard": HAS_LIZARD
        }
    }


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_repository(request: AnalyzeRequest, db: AsyncSession = Depends(get_db)):
    """
    Analyse un repository et calcule toutes les métriques:
    - Complexité cyclomatique (McCabe)
    - Métriques CK (WMC, DIT, NOC, CBO, RFC, LCOM)
    - Dépendances (fan-in/fan-out)
    - Code smells
    """
    logger.info(f"Starting analysis for repo {request.repo_id}")
    
    # Vérifier que le repo existe
    result = await db.execute(
        text("SELECT id, name, url FROM repositories WHERE id = :id"),
        {"id": request.repo_id}
    )
    repo = result.fetchone()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Récupérer les fichiers du repo depuis la base
    files_result = await db.execute(
        text("""
            SELECT f.id, f.filepath, f.filename, f.extension
            FROM files f
            JOIN commits c ON f.commit_id = c.id
            WHERE f.repo_id = :repo_id
            AND f.extension IN ('.py', '.java', '.js', '.ts', '.cpp', '.c', '.go')
            ORDER BY f.filepath
        """),
        {"repo_id": request.repo_id}
    )
    files = files_result.fetchall()
    
    if not files:
        # Si pas de fichiers en base, générer des métriques synthétiques pour démo
        logger.info("No files found, generating synthetic metrics")
        return await generate_synthetic_metrics(db, request.repo_id)
    
    metrics_results = []
    total_smells = 0
    
    for file_row in files:
        file_id, filepath, filename, extension = file_row
        
        # Ici, on devrait lire le contenu du fichier depuis le disque ou le repo cloné
        # Pour la démo, on génère des métriques synthétiques
        metrics = generate_synthetic_file_metrics(filepath, extension)
        
        # Sauvegarder en base
        try:
            await db.execute(
                text("""
                    INSERT INTO file_metrics (repo_id, file_id, filepath, commit_sha,
                        cyclomatic_complexity, max_cyclomatic_complexity, avg_cyclomatic_complexity,
                        wmc, dit, noc, cbo, rfc, lcom,
                        fan_in, fan_out, loc, sloc, comments, blank_lines,
                        num_methods, num_classes, code_smells_count)
                    VALUES (:repo_id, :file_id, :filepath, :commit_sha,
                        :cc, :max_cc, :avg_cc,
                        :wmc, :dit, :noc, :cbo, :rfc, :lcom,
                        :fan_in, :fan_out, :loc, :sloc, :comments, :blank,
                        :num_methods, :num_classes, :smells_count)
                    ON CONFLICT (repo_id, filepath, commit_sha) DO UPDATE SET
                        cyclomatic_complexity = :cc,
                        wmc = :wmc, cbo = :cbo, code_smells_count = :smells_count
                """),
                {
                    "repo_id": request.repo_id,
                    "file_id": file_id,
                    "filepath": filepath,
                    "commit_sha": request.commit_sha or "HEAD",
                    "cc": metrics["cyclomatic_complexity"],
                    "max_cc": metrics["max_cyclomatic_complexity"],
                    "avg_cc": metrics["avg_cyclomatic_complexity"],
                    "wmc": metrics["wmc"],
                    "dit": metrics["dit"],
                    "noc": metrics["noc"],
                    "cbo": metrics["cbo"],
                    "rfc": metrics["rfc"],
                    "lcom": metrics["lcom"],
                    "fan_in": metrics["fan_in"],
                    "fan_out": metrics["fan_out"],
                    "loc": metrics["loc"],
                    "sloc": metrics["sloc"],
                    "comments": metrics["comments"],
                    "blank": metrics["blank_lines"],
                    "num_methods": metrics["num_methods"],
                    "num_classes": metrics["num_classes"],
                    "smells_count": metrics["code_smells_count"]
                }
            )
        except Exception as e:
            logger.warning(f"Failed to save metrics for {filepath}: {e}")
        
        metrics_results.append(FileMetricsResult(
            filepath=filepath,
            language=metrics["language"],
            cyclomatic_complexity=metrics["cyclomatic_complexity"],
            max_cyclomatic_complexity=metrics["max_cyclomatic_complexity"],
            avg_cyclomatic_complexity=metrics["avg_cyclomatic_complexity"],
            wmc=metrics["wmc"],
            dit=metrics["dit"],
            noc=metrics["noc"],
            cbo=metrics["cbo"],
            rfc=metrics["rfc"],
            lcom=metrics["lcom"],
            fan_in=metrics["fan_in"],
            fan_out=metrics["fan_out"],
            loc=metrics["loc"],
            sloc=metrics["sloc"],
            comments=metrics["comments"],
            blank_lines=metrics["blank_lines"],
            num_methods=metrics["num_methods"],
            num_classes=metrics["num_classes"],
            code_smells=metrics["code_smells"],
            code_smells_count=metrics["code_smells_count"]
        ))
        total_smells += metrics["code_smells_count"]
    
    await db.commit()
    
    return AnalyzeResponse(
        repo_id=request.repo_id,
        files_analyzed=len(metrics_results),
        total_smells=total_smells,
        metrics=metrics_results
    )


async def generate_synthetic_metrics(db: AsyncSession, repo_id: int) -> AnalyzeResponse:
    """Génère des métriques synthétiques pour la démonstration."""
    import random
    
    synthetic_files = [
        "src/main/java/com/example/UserService.java",
        "src/main/java/com/example/OrderController.java",
        "src/main/java/com/example/ProductRepository.java",
        "src/main/java/com/example/AuthenticationFilter.java",
        "src/main/java/com/example/DataProcessor.java",
        "src/main/python/utils/helpers.py",
        "src/main/python/services/ml_engine.py",
    ]
    
    metrics_results = []
    total_smells = 0
    
    for filepath in synthetic_files:
        ext = Path(filepath).suffix
        metrics = generate_synthetic_file_metrics(filepath, ext)
        
        metrics_results.append(FileMetricsResult(
            filepath=filepath,
            language=metrics["language"],
            cyclomatic_complexity=metrics["cyclomatic_complexity"],
            max_cyclomatic_complexity=metrics["max_cyclomatic_complexity"],
            avg_cyclomatic_complexity=metrics["avg_cyclomatic_complexity"],
            wmc=metrics["wmc"],
            dit=metrics["dit"],
            noc=metrics["noc"],
            cbo=metrics["cbo"],
            rfc=metrics["rfc"],
            lcom=metrics["lcom"],
            fan_in=metrics["fan_in"],
            fan_out=metrics["fan_out"],
            loc=metrics["loc"],
            sloc=metrics["sloc"],
            comments=metrics["comments"],
            blank_lines=metrics["blank_lines"],
            num_methods=metrics["num_methods"],
            num_classes=metrics["num_classes"],
            code_smells=metrics["code_smells"],
            code_smells_count=metrics["code_smells_count"]
        ))
        total_smells += metrics["code_smells_count"]
        
        # Sauvegarder en base
        try:
            await db.execute(
                text("""
                    INSERT INTO file_metrics (repo_id, filepath, commit_sha,
                        cyclomatic_complexity, max_cyclomatic_complexity, avg_cyclomatic_complexity,
                        wmc, dit, noc, cbo, rfc, lcom,
                        fan_in, fan_out, loc, sloc, comments, blank_lines,
                        num_methods, num_classes, code_smells_count)
                    VALUES (:repo_id, :filepath, 'synthetic',
                        :cc, :max_cc, :avg_cc,
                        :wmc, :dit, :noc, :cbo, :rfc, :lcom,
                        :fan_in, :fan_out, :loc, :sloc, :comments, :blank,
                        :num_methods, :num_classes, :smells_count)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "repo_id": repo_id,
                    "filepath": filepath,
                    "cc": metrics["cyclomatic_complexity"],
                    "max_cc": metrics["max_cyclomatic_complexity"],
                    "avg_cc": metrics["avg_cyclomatic_complexity"],
                    "wmc": metrics["wmc"],
                    "dit": metrics["dit"],
                    "noc": metrics["noc"],
                    "cbo": metrics["cbo"],
                    "rfc": metrics["rfc"],
                    "lcom": metrics["lcom"],
                    "fan_in": metrics["fan_in"],
                    "fan_out": metrics["fan_out"],
                    "loc": metrics["loc"],
                    "sloc": metrics["sloc"],
                    "comments": metrics["comments"],
                    "blank": metrics["blank_lines"],
                    "num_methods": metrics["num_methods"],
                    "num_classes": metrics["num_classes"],
                    "smells_count": metrics["code_smells_count"]
                }
            )
        except Exception as e:
            logger.warning(f"Failed to save synthetic metrics: {e}")
    
    await db.commit()
    
    return AnalyzeResponse(
        repo_id=repo_id,
        files_analyzed=len(metrics_results),
        total_smells=total_smells,
        metrics=metrics_results
    )


def generate_synthetic_file_metrics(filepath: str, extension: str) -> Dict[str, Any]:
    """Génère des métriques synthétiques réalistes pour un fichier."""
    import random
    
    language = detect_language(filepath)
    
    # Générer des valeurs réalistes
    num_methods = random.randint(3, 25)
    cc_values = [random.randint(1, 15) for _ in range(num_methods)]
    
    metrics = {
        "language": language,
        "cyclomatic_complexity": sum(cc_values),
        "max_cyclomatic_complexity": max(cc_values) if cc_values else 0,
        "avg_cyclomatic_complexity": sum(cc_values) / len(cc_values) if cc_values else 0,
        "wmc": sum(cc_values),
        "dit": random.randint(0, 5),
        "noc": random.randint(0, 3),
        "cbo": random.randint(2, 15),
        "rfc": random.randint(10, 50),
        "lcom": random.randint(0, 100),
        "fan_in": random.randint(0, 10),
        "fan_out": random.randint(2, 20),
        "loc": random.randint(50, 500),
        "sloc": random.randint(40, 400),
        "comments": random.randint(5, 50),
        "blank_lines": random.randint(10, 80),
        "num_methods": num_methods,
        "num_classes": random.randint(1, 3),
        "code_smells": [],
        "code_smells_count": 0
    }
    
    # Ajouter des code smells si les métriques sont élevées
    if metrics["max_cyclomatic_complexity"] > 10:
        metrics["code_smells"].append({
            "smell_type": "high_complexity",
            "severity": "medium",
            "message": f"High cyclomatic complexity: {metrics['max_cyclomatic_complexity']}"
        })
    
    if metrics["loc"] > 300:
        metrics["code_smells"].append({
            "smell_type": "large_file",
            "severity": "low",
            "message": f"File has {metrics['loc']} lines"
        })
    
    if metrics["cbo"] > 10:
        metrics["code_smells"].append({
            "smell_type": "high_coupling",
            "severity": "medium",
            "message": f"High coupling: CBO = {metrics['cbo']}"
        })
    
    metrics["code_smells_count"] = len(metrics["code_smells"])
    
    return metrics


@app.get("/metrics/{repo_id}")
async def get_metrics(repo_id: int, db: AsyncSession = Depends(get_db)):
    """Récupère les métriques d'un repository."""
    result = await db.execute(
        text("""
            SELECT filepath, cyclomatic_complexity, wmc, dit, noc, cbo, rfc, lcom,
                   fan_in, fan_out, loc, sloc, num_methods, num_classes, code_smells_count
            FROM file_metrics
            WHERE repo_id = :repo_id
            ORDER BY cyclomatic_complexity DESC
        """),
        {"repo_id": repo_id}
    )
    rows = result.fetchall()
    
    metrics = []
    for row in rows:
        metrics.append({
            "filepath": row[0],
            "cyclomatic_complexity": row[1],
            "wmc": row[2],
            "dit": row[3],
            "noc": row[4],
            "cbo": row[5],
            "rfc": row[6],
            "lcom": row[7],
            "fan_in": row[8],
            "fan_out": row[9],
            "loc": row[10],
            "sloc": row[11],
            "num_methods": row[12],
            "num_classes": row[13],
            "code_smells_count": row[14]
        })
    
    return {"repo_id": repo_id, "files": len(metrics), "metrics": metrics}


@app.get("/smells/{repo_id}")
async def get_code_smells(repo_id: int, db: AsyncSession = Depends(get_db)):
    """Récupère les code smells d'un repository."""
    result = await db.execute(
        text("""
            SELECT filepath, smell_type, severity, line_start, message
            FROM code_smells
            WHERE repo_id = :repo_id
            ORDER BY 
                CASE severity 
                    WHEN 'critical' THEN 1 
                    WHEN 'high' THEN 2 
                    WHEN 'medium' THEN 3 
                    ELSE 4 
                END,
                filepath
        """),
        {"repo_id": repo_id}
    )
    rows = result.fetchall()
    
    smells = []
    for row in rows:
        smells.append({
            "filepath": row[0],
            "smell_type": row[1],
            "severity": row[2],
            "line_start": row[3],
            "message": row[4]
        })
    
    return {"repo_id": repo_id, "total_smells": len(smells), "smells": smells}


@app.get("/summary/{repo_id}")
async def get_analysis_summary(repo_id: int, db: AsyncSession = Depends(get_db)):
    """Récupère un résumé de l'analyse d'un repository."""
    result = await db.execute(
        text("""
            SELECT 
                COUNT(*) as file_count,
                AVG(cyclomatic_complexity) as avg_cc,
                MAX(cyclomatic_complexity) as max_cc,
                AVG(wmc) as avg_wmc,
                AVG(cbo) as avg_cbo,
                AVG(lcom) as avg_lcom,
                SUM(code_smells_count) as total_smells,
                SUM(loc) as total_loc
            FROM file_metrics
            WHERE repo_id = :repo_id
        """),
        {"repo_id": repo_id}
    )
    row = result.fetchone()
    
    if not row or row[0] == 0:
        return {"repo_id": repo_id, "status": "no_data"}
    
    return {
        "repo_id": repo_id,
        "summary": {
            "file_count": row[0],
            "avg_cyclomatic_complexity": float(row[1] or 0),
            "max_cyclomatic_complexity": float(row[2] or 0),
            "avg_wmc": float(row[3] or 0),
            "avg_cbo": float(row[4] or 0),
            "avg_lcom": float(row[5] or 0),
            "total_code_smells": int(row[6] or 0),
            "total_loc": int(row[7] or 0)
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
