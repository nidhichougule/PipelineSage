import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
import httpx

from app.core.config import Settings, get_settings
from app.models.schemas import (
    JobStepSummary,
    JobSummary,
    RateLimitInfo,
    RepositorySummary,
    RunJobsResponse,
    WorkflowRunSummary,
    WorkflowRunsResponse,
)
from app.utils.logger import logger


class GitHubServiceError(Exception):
    """Base exception for GitHub API interactions."""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class GitHubAuthError(GitHubServiceError):
    """Raised on invalid credentials or insufficient scope."""

    def __init__(self, message: str = "Invalid or expired GitHub credentials."):
        super().__init__(message, status_code=401)


class GitHubRateLimitError(GitHubServiceError):
    """Raised when GitHub API rate limits are exhausted."""

    def __init__(self, message: str, reset_timestamp: Optional[int] = None):
        super().__init__(message, status_code=429)
        self.reset_timestamp = reset_timestamp


class GitHubNotFoundError(GitHubServiceError):
    """Raised when a repository, workflow run, or job is not found."""

    def __init__(self, message: str = "Requested GitHub resource was not found."):
        super().__init__(message, status_code=404)


class GitHubLogExpiredError(GitHubServiceError):
    """Raised when logs have expired or been deleted per retention policy."""

    def __init__(self, message: str = "Logs for this job have expired or been purged (HTTP 410)."):
        super().__init__(message, status_code=410)


class GitHubAPIError(GitHubServiceError):
    """Raised on unexpected upstream GitHub API failures."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message, status_code=status_code)


class GitHubService:
    """Async client for interacting with the GitHub REST API (v3 / 2022-11-28)."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.settings = settings or get_settings()
        self._external_client = client

    def _get_headers(self) -> Dict[str, str]:
        """Construct secure headers, ensuring the token is masked in memory/logs."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "PipelineSage-Engine",
        }
        token = self.settings.GITHUB_PERSONAL_ACCESS_TOKEN
        if token and token.strip() and token != "your_github_pat_here":
            headers["Authorization"] = f"Bearer {token.strip()}"
        return headers

    def _sanitize_string(self, text: str) -> str:
        """Strip any accidental token appearance from error messages or logs."""
        token = self.settings.GITHUB_PERSONAL_ACCESS_TOKEN
        if token and token.strip() and len(token) > 5:
            return text.replace(token.strip(), "[REDACTED]")
        return text

    def _extract_rate_limit(self, response: httpx.Response) -> RateLimitInfo:
        """Extract rate limit quota metadata from response headers."""
        headers = response.headers
        try:
            limit = int(headers.get("x-ratelimit-limit", 60))
            remaining = int(headers.get("x-ratelimit-remaining", 60))
            reset_ts = int(headers.get("x-ratelimit-reset", 0)) if headers.get("x-ratelimit-reset") else None
            return RateLimitInfo(limit=limit, remaining=remaining, reset_timestamp=reset_ts)
        except (ValueError, TypeError):
            return RateLimitInfo(limit=60, remaining=60, reset_timestamp=None)

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Any, RateLimitInfo]:
        """Execute an asynchronous HTTP request against GitHub REST API."""
        url = f"{self.settings.GITHUB_API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
        headers = self._get_headers()

        async def _execute(c: httpx.AsyncClient):
            return await c.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                timeout=12.0,
            )

        try:
            if self._external_client:
                response = await _execute(self._external_client)
            else:
                async with httpx.AsyncClient() as client:
                    response = await _execute(client)
        except httpx.TimeoutException:
            logger.error(f"GitHub request timed out on {method} {path}")
            raise GitHubAPIError("GitHub API request timed out. Please try again.", status_code=504)
        except httpx.RequestError as exc:
            sanitized_err = self._sanitize_string(str(exc))
            logger.error(f"Network error during GitHub API request: {sanitized_err}")
            raise GitHubAPIError(f"Network error connecting to GitHub: {sanitized_err}", status_code=502)

        rate_limit = self._extract_rate_limit(response)

        # Handle HTTP Status Codes
        if response.status_code == 401:
            logger.warning("GitHub API returned 401 Unauthorized.")
            raise GitHubAuthError("GitHub authentication failed. Ensure token has read-only actions & metadata access.")

        if response.status_code == 403:
            if rate_limit.remaining == 0:
                logger.warning(f"GitHub API rate limit exhausted. Resets at {rate_limit.reset_timestamp}")
                raise GitHubRateLimitError(
                    "GitHub API rate limit exceeded. Please wait until quota resets.",
                    reset_timestamp=rate_limit.reset_timestamp,
                )
            raise GitHubAuthError("Access forbidden: Insufficient permissions for repository or action.")

        if response.status_code == 404:
            raise GitHubNotFoundError(f"Requested resource not found on GitHub: {path}")

        if response.status_code >= 500:
            logger.error(f"GitHub upstream error {response.status_code} on {path}")
            raise GitHubAPIError("GitHub service is currently unavailable.", status_code=502)

        try:
            payload = response.json()
        except Exception:
            payload = {}

        return payload, rate_limit

    async def get_repository(
        self,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> RepositorySummary:
        """Fetch repository metadata."""
        owner_val = owner or self.settings.GITHUB_OWNER
        repo_val = repo or self.settings.GITHUB_REPO

        data, _ = await self._request("GET", f"repos/{owner_val}/{repo_val}")
        return RepositorySummary(
            id=data["id"],
            name=data["name"],
            full_name=data["full_name"],
            private=data["private"],
            html_url=data["html_url"],
            default_branch=data.get("default_branch", "main"),
            description=data.get("description"),
        )

    async def get_workflow_runs(
        self,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 30,
    ) -> WorkflowRunsResponse:
        """Fetch list of workflow runs with pagination."""
        owner_val = owner or self.settings.GITHUB_OWNER
        repo_val = repo or self.settings.GITHUB_REPO

        params: Dict[str, Any] = {"page": page, "per_page": per_page}
        if status:
            params["status"] = status

        data, rate_limit = await self._request(
            "GET",
            f"repos/{owner_val}/{repo_val}/actions/runs",
            params=params,
        )

        runs: List[WorkflowRunSummary] = []
        for r in data.get("workflow_runs", []):
            runs.append(
                WorkflowRunSummary(
                    id=r["id"],
                    name=r.get("name", "Unknown Workflow"),
                    head_branch=r.get("head_branch"),
                    head_sha=r.get("head_sha", ""),
                    event=r.get("event", "push"),
                    status=r.get("status", "unknown"),
                    conclusion=r.get("conclusion"),
                    html_url=r.get("html_url", ""),
                    created_at=datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(r["updated_at"].replace("Z", "+00:00")),
                )
            )

        return WorkflowRunsResponse(
            total_count=data.get("total_count", len(runs)),
            page=page,
            per_page=per_page,
            rate_limit=rate_limit,
            runs=runs,
        )

    async def get_workflow_run(
        self,
        run_id: int,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> WorkflowRunSummary:
        """Fetch single workflow run details."""
        owner_val = owner or self.settings.GITHUB_OWNER
        repo_val = repo or self.settings.GITHUB_REPO

        r, _ = await self._request("GET", f"repos/{owner_val}/{repo_val}/actions/runs/{run_id}")
        return WorkflowRunSummary(
            id=r["id"],
            name=r.get("name", "Unknown Workflow"),
            head_branch=r.get("head_branch"),
            head_sha=r.get("head_sha", ""),
            event=r.get("event", "push"),
            status=r.get("status", "unknown"),
            conclusion=r.get("conclusion"),
            html_url=r.get("html_url", ""),
            created_at=datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(r["updated_at"].replace("Z", "+00:00")),
        )

    async def get_run_jobs(
        self,
        run_id: int,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> RunJobsResponse:
        """Fetch jobs and preserve all steps, identifying steps that failed."""
        owner_val = owner or self.settings.GITHUB_OWNER
        repo_val = repo or self.settings.GITHUB_REPO

        data, rate_limit = await self._request(
            "GET",
            f"repos/{owner_val}/{repo_val}/actions/runs/{run_id}/jobs",
        )

        jobs: List[JobSummary] = []
        for j in data.get("jobs", []):
            steps: List[JobStepSummary] = []
            failed_steps: List[str] = []

            for s in j.get("steps", []):
                step_obj = JobStepSummary(
                    number=s.get("number", 0),
                    name=s.get("name", "Step"),
                    status=s.get("status", "unknown"),
                    conclusion=s.get("conclusion"),
                )
                steps.append(step_obj)
                if s.get("conclusion") == "failure":
                    failed_steps.append(step_obj.name)

            started = (
                datetime.fromisoformat(j["started_at"].replace("Z", "+00:00"))
                if j.get("started_at")
                else None
            )
            completed = (
                datetime.fromisoformat(j["completed_at"].replace("Z", "+00:00"))
                if j.get("completed_at")
                else None
            )

            jobs.append(
                JobSummary(
                    id=j["id"],
                    run_id=j.get("run_id", run_id),
                    name=j.get("name", "Job"),
                    status=j.get("status", "unknown"),
                    conclusion=j.get("conclusion"),
                    html_url=j.get("html_url", ""),
                    started_at=started,
                    completed_at=completed,
                    steps=steps,
                    failed_steps=failed_steps,
                )
            )

        return RunJobsResponse(
            run_id=run_id,
            total_count=data.get("total_count", len(jobs)),
            rate_limit=rate_limit,
            jobs=jobs,
        )

    # Narrowly scoped, boundary-checked hostname patterns for GitHub Actions logs
    GITHUB_LOG_HOST_PATTERN = re.compile(
        r"^(?:[a-zA-Z0-9\-]+\.)*actions\.githubusercontent\.com$|^(?:[a-zA-Z0-9\-]+\.)*githubusercontent\.com$"
    )
    AWS_S3_LOG_HOST_PATTERN = re.compile(
        r"^(?:[a-zA-Z0-9\-]+(?:\.[a-zA-Z0-9\-]+)*\.)?s3(?:[.\-][a-zA-Z0-9\-]+)?\.amazonaws\.com$"
    )
    MAX_LOG_BYTES = 5 * 1024 * 1024  # 5 MB streaming ceiling

    async def get_job_raw_logs(
        self,
        job_id: int,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> Tuple[str, bool]:
        """Fetch raw job logs via explicit 302 redirect inspection and bounded streaming.

        Returns:
            Tuple[str, bool]: Decoded log content and a boolean indicating if it was truncated.
        """
        owner_val = owner or self.settings.GITHUB_OWNER
        repo_val = repo or self.settings.GITHUB_REPO

        url = f"{self.settings.GITHUB_API_BASE_URL.rstrip('/')}/repos/{owner_val}/{repo_val}/actions/jobs/{job_id}/logs"
        headers = self._get_headers()

        # Step 1: Intercept 302 Found explicitly without following redirects
        async def _fetch_redirect(c: httpx.AsyncClient):
            return await c.get(url, headers=headers, follow_redirects=False, timeout=10.0)

        try:
            if self._external_client:
                initial_resp = await _fetch_redirect(self._external_client)
            else:
                async with httpx.AsyncClient() as client:
                    initial_resp = await _fetch_redirect(client)
        except httpx.TimeoutException:
            raise GitHubAPIError("Timeout requesting job log redirect location.", status_code=504)
        except httpx.RequestError as exc:
            raise GitHubAPIError(f"Network error requesting job log URL: {self._sanitize_string(str(exc))}", status_code=502)

        if initial_resp.status_code == 401:
            raise GitHubAuthError("Authentication required to access job logs.")
        if initial_resp.status_code == 403:
            raise GitHubAuthError("Must have actions:read permission to download job logs.")
        if initial_resp.status_code == 404:
            raise GitHubNotFoundError(f"Logs for job ID {job_id} not found.")
        if initial_resp.status_code == 410:
            raise GitHubLogExpiredError(f"Logs for job ID {job_id} have expired or been deleted (HTTP 410).")
        if initial_resp.status_code != 302:
            raise GitHubAPIError(f"Expected HTTP 302 redirect for job logs, got {initial_resp.status_code}", status_code=502)

        redirect_url = initial_resp.headers.get("Location")
        if not redirect_url:
            raise GitHubAPIError("GitHub 302 redirect header missing 'Location'.", status_code=502)

        # Step 2: Validate redirect URL scheme, port, credentials, fragments, and hostname boundaries
        parsed = urlparse(redirect_url)
        if parsed.scheme != "https":
            raise GitHubAPIError("Insecure non-HTTPS log redirect rejected.", status_code=502)

        if parsed.username or parsed.password:
            raise GitHubAPIError("Log redirect URL containing embedded credentials rejected.", status_code=502)

        if parsed.port not in (None, 443):
            raise GitHubAPIError(f"Unexpected port in log redirect URL: {parsed.port}", status_code=502)

        if parsed.fragment:
            raise GitHubAPIError("Unexpected fragment in log redirect URL.", status_code=502)

        hostname = (parsed.hostname or "").lower()
        if not hostname:
            raise GitHubAPIError("Malformed log redirect URL with empty hostname.", status_code=502)

        is_allowed_host = bool(
            self.GITHUB_LOG_HOST_PATTERN.match(hostname)
            or self.AWS_S3_LOG_HOST_PATTERN.match(hostname)
        )
        if not is_allowed_host:
            logger.error(f"Rejected untrusted redirect host for logs: {hostname}")
            raise GitHubAPIError(f"Untrusted redirect host for logs: {hostname}", status_code=502)

        # Step 3: Stream download unauthenticated (strictly no Authorization header)
        byte_chunks: List[bytes] = []
        total_bytes = 0
        is_truncated = False

        download_timeout = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)
        unauth_headers = {"User-Agent": "PipelineSage-Engine"}

        try:
            async def _stream_download(dl_client: httpx.AsyncClient):
                nonlocal total_bytes, is_truncated
                async with dl_client.stream("GET", redirect_url, headers=unauth_headers, timeout=download_timeout) as stream_resp:
                    if stream_resp.status_code == 410:
                        raise GitHubLogExpiredError("Signed log download URL expired or purged (HTTP 410).")
                    if stream_resp.status_code in (401, 403):
                        raise GitHubAuthError("Signed download URL was rejected or expired.")
                    if stream_resp.status_code == 404:
                        raise GitHubNotFoundError("Log file not found at signed storage destination.")
                    if stream_resp.status_code >= 400:
                        raise GitHubAPIError(f"Failed to stream logs from storage host: HTTP {stream_resp.status_code}", status_code=502)

                    async for chunk in stream_resp.aiter_bytes(chunk_size=65536):
                        total_bytes += len(chunk)
                        if total_bytes > self.MAX_LOG_BYTES:
                            excess = total_bytes - self.MAX_LOG_BYTES
                            keep_bytes = len(chunk) - excess
                            if keep_bytes > 0:
                                byte_chunks.append(chunk[:keep_bytes])
                            is_truncated = True
                            await stream_resp.aclose()
                            break
                        byte_chunks.append(chunk)

            if self._external_client:
                await _stream_download(self._external_client)
            else:
                async with httpx.AsyncClient() as client:
                    await _stream_download(client)

        except GitHubServiceError:
            raise
        except httpx.TimeoutException:
            raise GitHubAPIError("Timeout while streaming log download from storage host.", status_code=504)
        except httpx.RequestError as exc:
            raise GitHubAPIError(f"Network error while streaming logs: {self._sanitize_string(str(exc))}", status_code=502)

        # Step 4: Safe UTF-8 decoding across chunk boundaries
        raw_bytes = b"".join(byte_chunks)
        log_text = raw_bytes.decode("utf-8", errors="replace")
        return log_text, is_truncated
