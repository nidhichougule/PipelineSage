from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.analyzers.log_parser import LogParser
from app.models.schemas import LogParseRequest, ParsedError
from app.routes.github import get_github_service
from app.services.github_service import (
    GitHubAuthError,
    GitHubLogExpiredError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubService,
    GitHubServiceError,
)

router = APIRouter(prefix="/api/v1/parser", tags=["Log Parser & Error Extraction"])


def get_log_parser() -> LogParser:
    """Dependency provider for pure Python LogParser instance."""
    return LogParser()


@router.post(
    "/parse",
    response_model=ParsedError,
    summary="Parse Raw Log Stream",
    description="Stateless endpoint that accepts up to 5 MB of raw CI log text and extracts error signatures, stack frames, and context.",
)
async def parse_raw_log(
    request: LogParseRequest,
    parser: LogParser = Depends(get_log_parser),
) -> ParsedError:
    return parser.parse(
        raw_logs=request.raw_logs,
        failed_step_hint=request.failed_step_hint,
        is_truncated=False,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=ParsedError,
    summary="Retrieve and Parse Workflow Job Logs",
    description="Fetches raw logs for a specific GitHub Actions job via explicit 302 redirect and streams them safely into the log parser.",
)
async def parse_job_logs(
    job_id: int,
    owner: Optional[str] = Query(None, description="GitHub repository owner"),
    repo: Optional[str] = Query(None, description="GitHub repository name"),
    service: GitHubService = Depends(get_github_service),
    parser: LogParser = Depends(get_log_parser),
) -> ParsedError:
    try:
        raw_logs, is_truncated = await service.get_job_raw_logs(
            job_id=job_id,
            owner=owner,
            repo=repo,
        )
    except GitHubAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message)
    except GitHubNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    except GitHubLogExpiredError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=exc.message)
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=exc.message)
    except GitHubServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    return parser.parse(
        raw_logs=raw_logs,
        failed_step_hint=None,
        is_truncated=is_truncated,
    )
