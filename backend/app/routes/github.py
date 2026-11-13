from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.models.schemas import (
    RepositorySummary,
    RunJobsResponse,
    WorkflowRunSummary,
    WorkflowRunsResponse,
)
from app.services.github_service import (
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubService,
    GitHubServiceError,
)

router = APIRouter(prefix="/api/v1/github", tags=["GitHub Integration"])


def get_github_service() -> GitHubService:
    """Dependency provider for GitHubService."""
    return GitHubService()


@router.get(
    "/repo",
    response_model=RepositorySummary,
    summary="Get Configured Repository Summary",
    description="Retrieves metadata for the target GitHub repository.",
)
async def get_repository_info(
    owner: Optional[str] = Query(None, description="GitHub repository owner (defaults to config)"),
    repo: Optional[str] = Query(None, description="GitHub repository name (defaults to config)"),
    service: GitHubService = Depends(get_github_service),
) -> RepositorySummary:
    try:
        return await service.get_repository(owner=owner, repo=repo)
    except GitHubAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message)
    except GitHubNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.message)
    except GitHubServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.get(
    "/runs",
    response_model=WorkflowRunsResponse,
    summary="List Workflow Runs",
    description="Fetches a paginated list of GitHub Actions workflow runs for the repository.",
)
async def list_workflow_runs(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (e.g. success, failure)"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(30, ge=1, le=100, description="Items per page"),
    owner: Optional[str] = Query(None, description="GitHub repository owner"),
    repo: Optional[str] = Query(None, description="GitHub repository name"),
    service: GitHubService = Depends(get_github_service),
) -> WorkflowRunsResponse:
    try:
        return await service.get_workflow_runs(
            owner=owner,
            repo=repo,
            status=status_filter,
            page=page,
            per_page=per_page,
        )
    except GitHubAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message)
    except GitHubNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.message)
    except GitHubServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.get(
    "/runs/{run_id}",
    response_model=WorkflowRunSummary,
    summary="Get Workflow Run Details",
    description="Retrieves execution details for a specific workflow run ID.",
)
async def get_workflow_run_details(
    run_id: int,
    owner: Optional[str] = Query(None, description="GitHub repository owner"),
    repo: Optional[str] = Query(None, description="GitHub repository name"),
    service: GitHubService = Depends(get_github_service),
) -> WorkflowRunSummary:
    try:
        return await service.get_workflow_run(run_id=run_id, owner=owner, repo=repo)
    except GitHubAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message)
    except GitHubNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.message)
    except GitHubServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


@router.get(
    "/runs/{run_id}/jobs",
    response_model=RunJobsResponse,
    summary="Get Jobs and Steps for Workflow Run",
    description="Retrieves all jobs and their constituent execution steps, flagging failing steps.",
)
async def get_workflow_run_jobs(
    run_id: int,
    owner: Optional[str] = Query(None, description="GitHub repository owner"),
    repo: Optional[str] = Query(None, description="GitHub repository name"),
    service: GitHubService = Depends(get_github_service),
) -> RunJobsResponse:
    try:
        return await service.get_run_jobs(run_id=run_id, owner=owner, repo=repo)
    except GitHubAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message)
    except GitHubNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.message)
    except GitHubServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
