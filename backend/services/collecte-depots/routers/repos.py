"""
Router des repositories
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging
import httpx
import json
import traceback

from database import get_db
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def parse_iso_date(date_string: Optional[str]) -> Optional[datetime]:
    """Parse ISO 8601 date string to naive datetime object."""
    if not date_string:
        return None
    try:
        # Handle ISO format with Z suffix
        if date_string.endswith('Z'):
            date_string = date_string[:-1]
        dt = datetime.fromisoformat(date_string)
        return dt.replace(tzinfo=None) # Make it naive for TIMESTAMP column
    except (ValueError, TypeError):
        return None


# ============ Schemas ============

class RepoCreate(BaseModel):
    name: str
    url: str
    provider: Optional[str] = "github"
    default_branch: Optional[str] = "main"


class RepoResponse(BaseModel):
    id: int
    name: str
    url: str
    provider: str
    default_branch: Optional[str] = "main"
    created_at: Optional[datetime] = None
    last_collected_at: Optional[datetime] = None
    status: Optional[str] = "active"


class CollectionResult(BaseModel):
    status: str
    commits_collected: int
    commits_stored: int
    files_stored: int
    issues_collected: int
    issues_stored: int


# ============ Endpoints ============

@router.get("", response_model=List[RepoResponse])
async def list_repos(db: AsyncSession = Depends(get_db)):
    """Liste tous les repositories."""
    result = await db.execute(
        text("SELECT id, name, url, provider, default_branch, created_at, last_collected_at, status FROM repositories ORDER BY created_at DESC")
    )
    rows = result.fetchall()
    return [
        RepoResponse(
            id=row[0],
            name=row[1],
            url=row[2],
            provider=row[3],
            default_branch=row[4],
            created_at=row[5],
            last_collected_at=row[6],
            status=row[7]
        )
        for row in rows
    ]


@router.post("", response_model=RepoResponse)
async def create_repo(repo: RepoCreate, db: AsyncSession = Depends(get_db)):
    """Crée un nouveau repository."""
    # Normaliser l'URL (retirer .git et trailing slash)
    normalized_url = repo.url.strip()
    if normalized_url.endswith('.git'):
        normalized_url = normalized_url[:-4]
    if normalized_url.endswith('/'):
        normalized_url = normalized_url[:-1]
    
    try:
        # Vérifier si le repo existe déjà
        existing = await db.execute(
            text("SELECT id, name, url, provider, default_branch, created_at, status FROM repositories WHERE url = :url OR url = :url_git"),
            {"url": normalized_url, "url_git": normalized_url + ".git"}
        )
        existing_row = existing.fetchone()
        if existing_row:
            # Retourner le repo existant
            return RepoResponse(
                id=existing_row[0],
                name=existing_row[1],
                url=existing_row[2],
                provider=existing_row[3],
                default_branch=existing_row[4],
                created_at=existing_row[5],
                status=existing_row[6]
            )
        
        result = await db.execute(
            text("""
                INSERT INTO repositories (name, url, provider, default_branch)
                VALUES (:name, :url, :provider, :default_branch)
                RETURNING id, name, url, provider, default_branch, created_at, status
            """),
            {
                "name": repo.name,
                "url": normalized_url,
                "provider": repo.provider,
                "default_branch": repo.default_branch
            }
        )
        await db.commit()
        row = result.fetchone()
        
        return RepoResponse(
            id=row[0],
            name=row[1],
            url=row[2],
            provider=row[3],
            default_branch=row[4],
            created_at=row[5],
            status=row[6]
        )
    except Exception as e:
        await db.rollback()
        if "unique" in str(e).lower():
            raise HTTPException(status_code=400, detail="Repository URL already exists")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{repo_id}", response_model=RepoResponse)
async def get_repo(repo_id: int, db: AsyncSession = Depends(get_db)):
    """Récupère un repository par son ID."""
    result = await db.execute(
        text("SELECT id, name, url, provider, default_branch, created_at, last_collected_at, status FROM repositories WHERE id = :id"),
        {"id": repo_id}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    return RepoResponse(
        id=row[0],
        name=row[1],
        url=row[2],
        provider=row[3],
        default_branch=row[4],
        created_at=row[5],
        last_collected_at=row[6],
        status=row[7]
    )


@router.delete("/{repo_id}")
async def delete_repo(repo_id: int, db: AsyncSession = Depends(get_db)):
    """Supprime un repository."""
    result = await db.execute(
        text("DELETE FROM repositories WHERE id = :id RETURNING id"),
        {"id": repo_id}
    )
    await db.commit()
    
    if result.fetchone() is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    return {"status": "deleted", "id": repo_id}


@router.post("/{repo_id}/collect", response_model=CollectionResult)
async def collect_repo(repo_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Lance la collecte des données d'un repository."""
    # Vérifier que le repo existe
    result = await db.execute(
        text("SELECT id, url, provider FROM repositories WHERE id = :id"),
        {"id": repo_id}
    )
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    repo_url = row[1]
    provider = row[2]
    
    # Simuler la collecte (en production, cela clonerait le repo et analyserait les commits)
    commits_collected = 0
    commits_stored = 0
    files_stored = 0
    issues_collected = 0
    issues_stored = 0
    
    try:
        # Collecter via GitHub API si c'est un repo GitHub
        github_success = False
        if provider == "github" and "github.com" in repo_url:
            # Parser l'URL pour extraire owner/repo
            parts = repo_url.rstrip("/").split("/")
            if len(parts) >= 2:
                owner = parts[-2]
                repo_name = parts[-1].replace(".git", "")
                
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        headers = {}
                        if settings.GITHUB_TOKEN:
                            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"
                        
                        # Récupérer les commits
                        commits_resp = await client.get(
                            f"https://api.github.com/repos/{owner}/{repo_name}/commits",
                            headers=headers,
                            params={"per_page": 100}
                        )
                        
                        if commits_resp.status_code == 200:
                            github_success = True
                            commits = commits_resp.json()
                            commits_collected = len(commits)
                            
                            for commit in commits:
                                sha = commit.get("sha", "")
                                message = commit.get("commit", {}).get("message", "")
                                author = commit.get("commit", {}).get("author", {})
                                
                                # Détecter si c'est un bugfix
                                is_bugfix = any(word in message.lower() for word in ["fix", "bug", "issue", "error", "patch"])
                                
                                parsed_date = parse_iso_date(author.get("date"))
                                
                                try:
                                    await db.execute(
                                        text("""
                                            INSERT INTO commits (repo_id, sha, message, author_name, author_email, is_bugfix, committed_at)
                                            VALUES (:repo_id, :sha, :message, :author_name, :author_email, :is_bugfix, :committed_at)
                                            ON CONFLICT (repo_id, sha) DO NOTHING
                                        """),
                                        {
                                            "repo_id": repo_id,
                                            "sha": sha,
                                            "message": message[:500] if message else "",
                                            "author_name": author.get("name", "Unknown"),
                                            "author_email": author.get("email", ""),
                                            "is_bugfix": is_bugfix,
                                            "committed_at": parsed_date
                                        }
                                    )
                                    commits_stored += 1
                                except Exception as e:
                                    logger.error(f"Failed to insert commit {sha}: {e}")
                                    continue
                except (httpx.ConnectError, httpx.TimeoutException, Exception) as e:
                    logger.warning(f"GitHub API not available: {e}. Using demo data.")
                    github_success = False
        
        # Si GitHub n'est pas disponible, générer des données de démonstration
        if not github_success:
            logger.info("Generating demo data for repository")
            demo_commits = [
                {"sha": f"demo{i}abc123def456", "message": f"Demo commit {i}: {'Fix bug' if i % 3 == 0 else 'Feature update'}", 
                 "author_name": "Demo Author", "author_email": "demo@example.com", "is_bugfix": i % 3 == 0}
                for i in range(20)
            ]
            
            for commit in demo_commits:
                try:
                    await db.execute(
                        text("""
                            INSERT INTO commits (repo_id, sha, message, author_name, author_email, is_bugfix, committed_at)
                            VALUES (:repo_id, :sha, :message, :author_name, :author_email, :is_bugfix, CURRENT_TIMESTAMP)
                            ON CONFLICT (repo_id, sha) DO NOTHING
                        """),
                        {
                            "repo_id": repo_id,
                            "sha": commit["sha"],
                            "message": commit["message"],
                            "author_name": commit["author_name"],
                            "author_email": commit["author_email"],
                            "is_bugfix": commit["is_bugfix"]
                        }
                    )
                    commits_stored += 1
                except Exception as e:
                    logger.error(f"Failed to insert demo commit: {e}")
            
            commits_collected = len(demo_commits)
        
        # Mettre à jour la date de dernière collecte
        await db.execute(
            text("UPDATE repositories SET last_collected_at = CURRENT_TIMESTAMP WHERE id = :id"),
            {"id": repo_id}
        )
        await db.commit()
        
        return CollectionResult(
            status="success" if github_success else "demo_data",
            commits_collected=commits_collected,
            commits_stored=commits_stored,
            files_stored=files_stored,
            issues_collected=issues_collected,
            issues_stored=issues_stored
        )
        
    except Exception as e:
        await db.rollback()
        error_msg = traceback.format_exc()
        print(f"COLLECTION ERROR: {error_msg}")
        logger.error(f"Collection failed: {error_msg}")
        # Return the actual error message in the detail
        raise HTTPException(status_code=500, detail=f"Database error during collection: {str(e)}\n{error_msg}")


@router.get("/{repo_id}/commits")
async def get_repo_commits(repo_id: int, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Récupère les commits d'un repository."""
    result = await db.execute(
        text("""
            SELECT id, sha, message, author_name, is_bugfix, committed_at 
            FROM commits 
            WHERE repo_id = :repo_id 
            ORDER BY committed_at DESC 
            LIMIT :limit
        """),
        {"repo_id": repo_id, "limit": limit}
    )
    rows = result.fetchall()
    
    return [
        {
            "id": row[0],
            "sha": row[1],
            "message": row[2],
            "author_name": row[3],
            "is_bugfix": row[4],
            "committed_at": row[5]
        }
        for row in rows
    ]


@router.get("/{repo_id}/metrics")
async def get_repo_metrics(repo_id: int, db: AsyncSession = Depends(get_db)):
    """Récupère les métriques d'un repository."""
    # Compter les commits
    commits_result = await db.execute(
        text("SELECT COUNT(*), SUM(CASE WHEN is_bugfix THEN 1 ELSE 0 END) FROM commits WHERE repo_id = :id"),
        {"id": repo_id}
    )
    commits_row = commits_result.fetchone()
    
    # Compter les issues
    issues_result = await db.execute(
        text("SELECT COUNT(*), SUM(CASE WHEN is_bug THEN 1 ELSE 0 END) FROM issues WHERE repo_id = :id"),
        {"id": repo_id}
    )
    issues_row = issues_result.fetchone()
    
    # Récupérer les métriques de fichiers
    metrics_result = await db.execute(
        text("""
            SELECT 
                AVG(cyclomatic_complexity) as avg_complexity,
                AVG(wmc) as avg_wmc,
                AVG(cbo) as avg_cbo,
                SUM(code_smells_count) as total_smells,
                COUNT(*) as total_files
            FROM file_metrics 
            WHERE repo_id = :id
        """),
        {"id": repo_id}
    )
    metrics_row = metrics_result.fetchone()
    
    return {
        "repo_id": repo_id,
        "commits": {
            "total": commits_row[0] or 0,
            "bugfixes": commits_row[1] or 0
        },
        "issues": {
            "total": issues_row[0] or 0,
            "bugs": issues_row[1] or 0
        },
        "code_metrics": {
            "avg_complexity": float(metrics_row[0] or 0),
            "avg_wmc": float(metrics_row[1] or 0),
            "avg_cbo": float(metrics_row[2] or 0),
            "total_smells": int(metrics_row[3] or 0),
            "total_files": int(metrics_row[4] or 0)
        }
    }
