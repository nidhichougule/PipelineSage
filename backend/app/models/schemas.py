from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for health status response."""

    status: str = Field(default="healthy", description="Current service health status")
    app_name: str = Field(..., description="Name of the application")
    app_version: str = Field(..., description="Semver version of the application")
    environment: str = Field(..., description="Active runtime environment")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Current UTC timestamp of the healthcheck",
    )


class RootResponse(BaseModel):
    """Schema for root API greeting response."""

    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    description: str = Field(..., description="High-level description of the system")
    docs_url: str = Field(..., description="Interactive Swagger documentation URL")
    health_url: str = Field(..., description="Health check endpoint URL")


class ErrorResponse(BaseModel):
    """Standardized error response schema."""

    success: bool = Field(default=False, description="Flag indicating failure")
    detail: str = Field(..., description="Human-readable error explanation")
    error_code: Optional[str] = Field(default=None, description="Categorized machine-readable error code")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the error",
    )


# --- GitHub API Schemas ---


class RateLimitInfo(BaseModel):
    """Rate limit quota metadata extracted from GitHub response headers."""

    limit: int = Field(default=60, description="Total request quota per hour")
    remaining: int = Field(default=60, description="Remaining requests in the current window")
    reset_timestamp: Optional[int] = Field(default=None, description="Unix timestamp when quota resets")


class RepositorySummary(BaseModel):
    """Summary of GitHub repository metadata."""

    id: int
    name: str
    full_name: str
    private: bool
    html_url: str
    default_branch: str
    description: Optional[str] = None


class WorkflowRunSummary(BaseModel):
    """Summary representation of a GitHub Actions workflow run."""

    id: int
    name: str
    head_branch: Optional[str] = None
    head_sha: str
    event: str
    status: str
    conclusion: Optional[str] = None
    html_url: str
    created_at: datetime
    updated_at: datetime


class WorkflowRunsResponse(BaseModel):
    """Paginated collection of workflow runs."""

    total_count: int
    page: int
    per_page: int
    rate_limit: RateLimitInfo
    runs: List[WorkflowRunSummary]


class JobStepSummary(BaseModel):
    """Detailed metadata for a single step inside a job."""

    number: int
    name: str
    status: str
    conclusion: Optional[str] = None


class JobSummary(BaseModel):
    """Summary of a workflow job with preserved execution steps."""

    id: int
    run_id: int
    name: str
    status: str
    conclusion: Optional[str] = None
    html_url: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    steps: List[JobStepSummary] = Field(default_factory=list)
    failed_steps: List[str] = Field(default_factory=list, description="Names of steps with conclusion 'failure'")


class RunJobsResponse(BaseModel):
    """Jobs associated with a specific workflow run."""

    run_id: int
    total_count: int
    rate_limit: RateLimitInfo
    jobs: List[JobSummary]


# --- Log Parser Schemas ---


class StackFrame(BaseModel):
    """Representation of an individual stack trace frame."""

    file: str
    line: Optional[int] = None
    function: Optional[str] = None
    code_context: Optional[str] = None


class ParsedError(BaseModel):
    """Structured failure diagnosis extracted from raw logs."""

    has_error: bool = Field(default=True, description="Whether an error was detected in the log")
    error_type: Optional[str] = Field(default=None, description="Exception class or category")
    error_message: Optional[str] = Field(default=None, description="Detailed error description")
    normalized_signature: Optional[str] = Field(default=None, description="Canonical error signature")
    failed_step: Optional[str] = Field(default=None, description="Pipeline stage where failure occurred")
    failed_test: Optional[str] = Field(default=None, description="Full test identifier including parameterization")
    file_reference: Optional[str] = Field(default=None, description="Source file associated with failure")
    line_number: Optional[int] = Field(default=None, description="Line number of failure frame")
    stack_trace: List[StackFrame] = Field(default_factory=list, description="Extracted stack trace frames")
    context_lines: List[str] = Field(default_factory=list, description="Surrounding log excerpt around failure")
    is_truncated: bool = Field(default=False, description="Whether raw log exceeded 5 MB and was truncated")


class LogParseRequest(BaseModel):
    """Input payload for raw log parsing."""

    raw_logs: str = Field(..., max_length=5_242_880, description="Raw log stream up to 5 MB")
    failed_step_hint: Optional[str] = Field(default=None, description="Optional step name hint from job metadata")
