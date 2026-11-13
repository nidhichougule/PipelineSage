from fastapi import APIRouter, status
from app.core.config import get_settings
from app.models.schemas import HealthResponse

router = APIRouter(tags=["System Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Returns the operational status, current version, environment, and server timestamp.",
)
async def check_health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        environment=settings.APP_ENV,
    )
