import json
from datetime import datetime
import pytest
import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.routes.github import get_github_service
from app.services.github_service import (
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubService,
)


def make_mock_transport(handler):
    """Helper to create httpx.MockTransport from a callable handler."""
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_get_repository_success():
    """Verify repository metadata extraction and schema validation."""
    mock_payload = {
        "id": 987654,
        "name": "PipelineSage-demo",
        "full_name": "nidhichougule/PipelineSage-demo",
        "private": False,
        "html_url": "https://github.com/nidhichougule/PipelineSage-demo",
        "default_branch": "main",
        "description": "Controlled CI failure testbed",
    }

    def handler(request: httpx.Request):
        return httpx.Response(
            200,
            json=mock_payload,
            headers={"x-ratelimit-limit": "60", "x-ratelimit-remaining": "58"},
        )

    async with httpx.AsyncClient(transport=make_mock_transport(handler)) as client:
        service = GitHubService(client=client)
        repo = await service.get_repository("nidhichougule", "PipelineSage-demo")
        assert repo.id == 987654
        assert repo.name == "PipelineSage-demo"
        assert repo.default_branch == "main"
        assert repo.private is False


@pytest.mark.asyncio
async def test_get_workflow_runs_success():
    """Verify workflow runs collection and pagination metadata."""
    mock_payload = {
        "total_count": 1,
        "workflow_runs": [
            {
                "id": 1001,
                "name": "CI",
                "head_branch": "main",
                "head_sha": "d0dbad0a",
                "event": "push",
                "status": "completed",
                "conclusion": "success",
                "html_url": "https://github.com/nidhichougule/PipelineSage-demo/actions/runs/1001",
                "created_at": "2026-11-13T23:00:00Z",
                "updated_at": "2026-11-13T23:01:00Z",
            }
        ],
    }

    def handler(request: httpx.Request):
        return httpx.Response(
            200,
            json=mock_payload,
            headers={"x-ratelimit-limit": "60", "x-ratelimit-remaining": "55"},
        )

    async with httpx.AsyncClient(transport=make_mock_transport(handler)) as client:
        service = GitHubService(client=client)
        resp = await service.get_workflow_runs(page=1, per_page=10)
        assert resp.total_count == 1
        assert len(resp.runs) == 1
        assert resp.runs[0].id == 1001
        assert resp.runs[0].conclusion == "success"
        assert resp.rate_limit.remaining == 55


@pytest.mark.asyncio
async def test_get_run_jobs_identifies_failed_steps():
    """Verify all steps are preserved and failing steps are accurately flagged."""
    mock_payload = {
        "total_count": 1,
        "jobs": [
            {
                "id": 501,
                "run_id": 1002,
                "name": "Run CI Scenario",
                "status": "completed",
                "conclusion": "failure",
                "html_url": "https://github.com/nidhichougule/PipelineSage-demo/actions/runs/1002/job/501",
                "started_at": "2026-11-13T23:05:00Z",
                "completed_at": "2026-11-13T23:05:30Z",
                "steps": [
                    {"number": 1, "name": "Checkout", "status": "completed", "conclusion": "success"},
                    {"number": 2, "name": "Set up Python", "status": "completed", "conclusion": "success"},
                    {"number": 3, "name": "Execute Tests", "status": "completed", "conclusion": "failure"},
                ],
            }
        ],
    }

    def handler(request: httpx.Request):
        return httpx.Response(200, json=mock_payload)

    async with httpx.AsyncClient(transport=make_mock_transport(handler)) as client:
        service = GitHubService(client=client)
        resp = await service.get_run_jobs(run_id=1002)
        assert resp.total_count == 1
        job = resp.jobs[0]
        assert job.conclusion == "failure"
        assert len(job.steps) == 3
        # Ensure failed steps list strictly isolates the failure step
        assert job.failed_steps == ["Execute Tests"]


@pytest.mark.asyncio
async def test_github_auth_error_handling():
    """Verify HTTP 401 triggers GitHubAuthError."""
    def handler(request: httpx.Request):
        return httpx.Response(401, json={"message": "Bad credentials"})

    async with httpx.AsyncClient(transport=make_mock_transport(handler)) as client:
        service = GitHubService(client=client)
        with pytest.raises(GitHubAuthError) as exc_info:
            await service.get_repository()
        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_github_rate_limit_exhausted_handling():
    """Verify HTTP 403 with 0 remaining quota triggers GitHubRateLimitError."""
    def handler(request: httpx.Request):
        return httpx.Response(
            403,
            json={"message": "API rate limit exceeded"},
            headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1731542400"},
        )

    async with httpx.AsyncClient(transport=make_mock_transport(handler)) as client:
        service = GitHubService(client=client)
        with pytest.raises(GitHubRateLimitError) as exc_info:
            await service.get_repository()
        assert exc_info.value.status_code == 429
        assert exc_info.value.reset_timestamp == 1731542400


@pytest.mark.asyncio
async def test_github_not_found_handling():
    """Verify HTTP 404 triggers GitHubNotFoundError."""
    def handler(request: httpx.Request):
        return httpx.Response(404, json={"message": "Not Found"})

    async with httpx.AsyncClient(transport=make_mock_transport(handler)) as client:
        service = GitHubService(client=client)
        with pytest.raises(GitHubNotFoundError) as exc_info:
            await service.get_workflow_run(run_id=999999)
        assert exc_info.value.status_code == 404


def test_token_sanitization():
    """Verify sensitive tokens are never echoed in error strings."""
    secret_token = "ghp_SECRET_TOKEN_XYZ_12345"
    test_settings = Settings(GITHUB_PERSONAL_ACCESS_TOKEN=secret_token)
    service = GitHubService(settings=test_settings)

    leak_candidate = f"Failed to connect to host with token {secret_token} on port 443"
    sanitized = service._sanitize_string(leak_candidate)

    assert secret_token not in sanitized
    assert "[REDACTED]" in sanitized


def test_fastapi_github_routes_via_client(client: TestClient):
    """Verify FastAPI routes integrate cleanly with dependency injection."""
    class FakeGitHubService:
        async def get_repository(self, owner=None, repo=None):
            return {
                "id": 1234,
                "name": "PipelineSage-demo",
                "full_name": "nidhichougule/PipelineSage-demo",
                "private": False,
                "html_url": "https://github.com/nidhichougule/PipelineSage-demo",
                "default_branch": "main",
                "description": "Demo",
            }

    app.dependency_overrides[get_github_service] = lambda: FakeGitHubService()
    try:
        response = client.get("/api/v1/github/repo")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "PipelineSage-demo"
        assert data["id"] == 1234
    finally:
        app.dependency_overrides.clear()
