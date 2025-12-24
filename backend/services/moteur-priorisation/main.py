"""
Moteur de Priorisation
======================
Service d'optimisation pour la priorisation des tests avec OR-Tools.
Port: 8004

Selon le cahier de charges:
- Entrées/Sorties : Scores + contraintes → plan de tests priorisé (JSON)
- Technos : OR-Tools (optimisation), heuristiques effort-aware (Popt@20)
- Base : PostgreSQL (politiques/poids)
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
import numpy as np
from datetime import datetime
import logging
import json

# OR-Tools imports
try:
    from ortools.linear_solver import pywraplp
    from ortools.sat.python import cp_model
    HAS_ORTOOLS = True
except ImportError:
    HAS_ORTOOLS = False
    logging.warning("OR-Tools not available, using fallback heuristics")

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============ Configuration ============

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://ace_user:ace_password@localhost:5432/ace_db"
    REDIS_URL: str = "redis://localhost:6379"
    
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
    logger.info("Starting Moteur Priorisation service...")
    yield
    logger.info("Shutting down Moteur Priorisation service...")


# ============ Application FastAPI ============

app = FastAPI(
    title="ACE - Moteur de Priorisation",
    description="Service d'optimisation pour la priorisation des tests avec OR-Tools",
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

class PrioritizationItem(BaseModel):
    id: str
    risk: float  # Score de risque (0-1)
    effort: float  # Effort en unités
    criticite: Optional[float] = 1.0  # Criticité métier
    deps: Optional[List[str]] = None  # Dépendances
    module: Optional[str] = None
    coverage_gap: Optional[float] = 0.0
    risk_confidence: Optional[float] = 0.5


class SprintContext(BaseModel):
    capacity: Optional[int] = None
    time_remaining: Optional[int] = None
    max_items: Optional[int] = None
    mandatory_ids: Optional[List[str]] = None
    excluded_ids: Optional[List[str]] = None


class PrioritizationRequest(BaseModel):
    repo_id: Optional[int] = None
    items: List[PrioritizationItem]
    budget: int  # Budget d'effort total
    weights: Optional[Dict[str, float]] = None  # Poids pour les critères
    sprint_context: Optional[SprintContext] = None


class PrioritizationPlan(BaseModel):
    rank: int
    id: str
    module: Optional[str] = None
    selected: bool
    risk: float
    effort: float
    criticite: float
    priority_score: float
    selection_reason: str


class PrioritizationSummary(BaseModel):
    budget: int
    effort_selected: float
    items_selected: int
    items_total: int


class PrioritizationResponse(BaseModel):
    summary: PrioritizationSummary
    plan: List[PrioritizationPlan]


class HeuristicComparisonResult(BaseModel):
    heuristic: str
    items_selected: int
    effort_used: float
    total_risk_covered: float
    efficiency: float  # risk / effort


# ============ Optimization Functions ============

def calculate_priority_score(item: PrioritizationItem, weights: Dict[str, float]) -> float:
    """
    Calcule le score de priorité selon la formule effort-aware.
    """
    risk_weight = weights.get("risk", 1.0)
    crit_weight = weights.get("crit", 0.5)
    coverage_weight = weights.get("coverage", 0.2)
    
    # Score = (risk * weight + criticité * weight + coverage_gap * weight) / effort
    numerator = (
        item.risk * risk_weight +
        item.criticite * crit_weight +
        item.coverage_gap * coverage_weight
    )
    
    # Éviter la division par zéro
    effort = max(item.effort, 1)
    
    # Score effort-aware: maximiser la valeur par unité d'effort
    score = numerator / (effort ** 0.5)  # Racine carrée pour ne pas trop pénaliser les gros efforts
    
    return float(score)


def solve_with_ortools(
    items: List[PrioritizationItem],
    budget: int,
    weights: Dict[str, float],
    mandatory_ids: List[str] = None,
    excluded_ids: List[str] = None
) -> List[bool]:
    """
    Résout le problème de sac à dos avec OR-Tools.
    Maximise la valeur (risque × criticité) sous contrainte de budget d'effort.
    """
    if not HAS_ORTOOLS:
        return solve_with_heuristic(items, budget, weights)
    
    mandatory_ids = mandatory_ids or []
    excluded_ids = excluded_ids or []
    
    # Créer le solver
    solver = pywraplp.Solver.CreateSolver("SCIP")
    if not solver:
        solver = pywraplp.Solver.CreateSolver("CBC")
    
    if not solver:
        logger.warning("No solver available, using heuristic")
        return solve_with_heuristic(items, budget, weights)
    
    n = len(items)
    
    # Variables de décision: x[i] = 1 si l'item i est sélectionné
    x = [solver.BoolVar(f"x_{i}") for i in range(n)]
    
    # Contrainte de budget
    solver.Add(
        sum(items[i].effort * x[i] for i in range(n)) <= budget
    )
    
    # Contraintes obligatoires
    for i, item in enumerate(items):
        if item.id in mandatory_ids:
            solver.Add(x[i] == 1)
        if item.id in excluded_ids:
            solver.Add(x[i] == 0)
    
    # Objectif: maximiser la somme des scores de priorité
    objective = sum(
        calculate_priority_score(items[i], weights) * x[i]
        for i in range(n)
    )
    solver.Maximize(objective)
    
    # Résoudre
    status = solver.Solve()
    
    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        return [x[i].solution_value() > 0.5 for i in range(n)]
    else:
        logger.warning(f"Solver status: {status}, falling back to heuristic")
        return solve_with_heuristic(items, budget, weights)


def solve_with_heuristic(
    items: List[PrioritizationItem],
    budget: int,
    weights: Dict[str, float]
) -> List[bool]:
    """
    Résout avec une heuristique gloutonne effort-aware.
    Trie par ratio valeur/effort et sélectionne tant que le budget le permet.
    """
    n = len(items)
    
    # Calculer les scores et trier
    scored_items = [
        (i, calculate_priority_score(items[i], weights))
        for i in range(n)
    ]
    scored_items.sort(key=lambda x: x[1], reverse=True)
    
    # Sélection gloutonne
    selected = [False] * n
    remaining_budget = budget
    
    for i, score in scored_items:
        if items[i].effort <= remaining_budget:
            selected[i] = True
            remaining_budget -= items[i].effort
    
    return selected


def compare_heuristics(
    items: List[PrioritizationItem],
    budget: int,
    weights: Dict[str, float]
) -> List[HeuristicComparisonResult]:
    """
    Compare différentes heuristiques selon le cahier de charges:
    - Complexité seule
    - Couverture seule
    - Récenteté (non implémenté ici, utilise risk)
    - Effort-aware (notre approche principale)
    """
    results = []
    
    # 1. Heuristique basée sur le risque seul (complexité)
    risk_only = sorted(range(len(items)), key=lambda i: items[i].risk, reverse=True)
    selected_risk = []
    effort_used = 0
    for i in risk_only:
        if effort_used + items[i].effort <= budget:
            selected_risk.append(i)
            effort_used += items[i].effort
    
    total_risk_risk = sum(items[i].risk for i in selected_risk)
    results.append(HeuristicComparisonResult(
        heuristic="risk_only",
        items_selected=len(selected_risk),
        effort_used=effort_used,
        total_risk_covered=total_risk_risk,
        efficiency=total_risk_risk / max(effort_used, 1)
    ))
    
    # 2. Heuristique basée sur la couverture seule
    coverage_only = sorted(range(len(items)), key=lambda i: items[i].coverage_gap, reverse=True)
    selected_cov = []
    effort_used = 0
    for i in coverage_only:
        if effort_used + items[i].effort <= budget:
            selected_cov.append(i)
            effort_used += items[i].effort
    
    total_risk_cov = sum(items[i].risk for i in selected_cov)
    results.append(HeuristicComparisonResult(
        heuristic="coverage_only",
        items_selected=len(selected_cov),
        effort_used=effort_used,
        total_risk_covered=total_risk_cov,
        efficiency=total_risk_cov / max(effort_used, 1)
    ))
    
    # 3. Heuristique effort-aware (notre approche)
    selected_ea = solve_with_heuristic(items, budget, weights)
    selected_ea_idx = [i for i, s in enumerate(selected_ea) if s]
    effort_used = sum(items[i].effort for i in selected_ea_idx)
    total_risk_ea = sum(items[i].risk for i in selected_ea_idx)
    
    results.append(HeuristicComparisonResult(
        heuristic="effort_aware",
        items_selected=len(selected_ea_idx),
        effort_used=effort_used,
        total_risk_covered=total_risk_ea,
        efficiency=total_risk_ea / max(effort_used, 1)
    ))
    
    return results


# ============ Endpoints ============

@app.get("/")
async def root():
    return {
        "service": "moteur-priorisation",
        "version": "1.0.0",
        "status": "running",
        "ortools_available": HAS_ORTOOLS
    }


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected", "ortools": HAS_ORTOOLS}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}


@app.post("/prioritize", response_model=PrioritizationResponse)
async def prioritize(request: PrioritizationRequest, db: AsyncSession = Depends(get_db)):
    """
    Génère un plan de tests priorisé.
    Entrée: Scores + contraintes
    Sortie: Plan de tests priorisé (JSON)
    """
    logger.info(f"Prioritizing {len(request.items)} items with budget {request.budget}")
    
    if not request.items:
        raise HTTPException(status_code=400, detail="No items to prioritize")
    
    # Récupérer les poids par défaut si non fournis
    weights = request.weights or {"risk": 1.0, "crit": 0.5, "coverage": 0.2}
    
    # Contexte de sprint
    mandatory_ids = []
    excluded_ids = []
    if request.sprint_context:
        mandatory_ids = request.sprint_context.mandatory_ids or []
        excluded_ids = request.sprint_context.excluded_ids or []
    
    # Résoudre l'optimisation
    selected = solve_with_ortools(
        request.items,
        request.budget,
        weights,
        mandatory_ids,
        excluded_ids
    )
    
    # Calculer les scores de priorité pour tous les items
    scored_items = []
    for i, item in enumerate(request.items):
        score = calculate_priority_score(item, weights)
        scored_items.append((i, item, score, selected[i]))
    
    # Trier par score décroissant
    scored_items.sort(key=lambda x: x[2], reverse=True)
    
    # Construire le plan
    plan = []
    effort_selected = 0
    items_selected = 0
    
    for rank, (idx, item, score, is_selected) in enumerate(scored_items, 1):
        reason = ""
        if is_selected:
            reason = "Selected by optimization"
            effort_selected += item.effort
            items_selected += 1
            if item.id in mandatory_ids:
                reason = "Mandatory item"
        else:
            if item.id in excluded_ids:
                reason = "Excluded by constraint"
            elif effort_selected + item.effort > request.budget:
                reason = "Budget exceeded"
            else:
                reason = "Lower priority"
        
        plan.append(PrioritizationPlan(
            rank=rank,
            id=item.id,
            module=item.module,
            selected=is_selected,
            risk=item.risk,
            effort=item.effort,
            criticite=item.criticite,
            priority_score=score,
            selection_reason=reason
        ))
    
    # Sauvegarder le run en base si repo_id fourni
    if request.repo_id:
        try:
            await db.execute(
                text("""
                    INSERT INTO prioritization_runs (repo_id, budget, weights, items_total, 
                                                     items_selected, effort_total, effort_selected, plan)
                    VALUES (:repo_id, :budget, :weights, :items_total, :items_selected, 
                            :effort_total, :effort_selected, :plan)
                """),
                {
                    "repo_id": request.repo_id,
                    "budget": request.budget,
                    "weights": json.dumps(weights),
                    "items_total": len(request.items),
                    "items_selected": items_selected,
                    "effort_total": sum(item.effort for item in request.items),
                    "effort_selected": effort_selected,
                    "plan": json.dumps([p.dict() for p in plan])
                }
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to save prioritization run: {e}")
    
    return PrioritizationResponse(
        summary=PrioritizationSummary(
            budget=request.budget,
            effort_selected=effort_selected,
            items_selected=items_selected,
            items_total=len(request.items)
        ),
        plan=plan
    )


@app.post("/compare-heuristics")
async def compare_heuristics_endpoint(request: PrioritizationRequest):
    """
    Compare différentes heuristiques de priorisation.
    Utile pour l'évaluation comparative vs heuristiques (complexité seule, couverture seule).
    """
    weights = request.weights or {"risk": 1.0, "crit": 0.5, "coverage": 0.2}
    
    results = compare_heuristics(request.items, request.budget, weights)
    
    return {
        "budget": request.budget,
        "items_total": len(request.items),
        "comparisons": [r.dict() for r in results]
    }


@app.get("/policies")
async def get_policies(db: AsyncSession = Depends(get_db)):
    """Récupère les politiques de priorisation."""
    result = await db.execute(
        text("""
            SELECT id, name, description, risk_weight, criticite_weight, effort_weight,
                   coverage_weight, default_budget, is_default, is_active
            FROM prioritization_policies
            WHERE is_active = TRUE
            ORDER BY is_default DESC, name
        """)
    )
    rows = result.fetchall()
    
    policies = []
    for row in rows:
        policies.append({
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "weights": {
                "risk": row[3],
                "criticite": row[4],
                "effort": row[5],
                "coverage": row[6]
            },
            "default_budget": row[7],
            "is_default": row[8],
            "is_active": row[9]
        })
    
    return {"policies": policies}


@app.get("/runs/{repo_id}")
async def get_prioritization_runs(repo_id: int, limit: int = 10, db: AsyncSession = Depends(get_db)):
    """Récupère l'historique des priorisations pour un repo."""
    result = await db.execute(
        text("""
            SELECT id, budget, items_total, items_selected, effort_selected, created_at
            FROM prioritization_runs
            WHERE repo_id = :repo_id
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        {"repo_id": repo_id, "limit": limit}
    )
    rows = result.fetchall()
    
    runs = []
    for row in rows:
        runs.append({
            "id": row[0],
            "budget": row[1],
            "items_total": row[2],
            "items_selected": row[3],
            "effort_selected": row[4],
            "created_at": row[5].isoformat() if row[5] else None
        })
    
    return {"runs": runs}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
