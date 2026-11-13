from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for health status response."""

    status: str = Field(default="healthy", description="Current service health status")
    app_name: str = Field(..., description="Name of the application")
    app_version: str = Field(..., description="Semver version of the application")
    environment: str = Field(..., description="Active runtime environment (e.g., development, production)")
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
