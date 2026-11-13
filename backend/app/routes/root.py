from fastapi import APIRouter, status
from app.core.config import get_settings
from app.models.schemas import RootResponse

router = APIRouter(tags=["Root"])


@router.get(
    "/",
    response_model=RootResponse,
    status_code=status.HTTP_200_OK,
    summary="Root Service Information",
    description="Provides introductory service metadata and pointers to interactive API documentation.",
)
async def get_root() -> RootResponse:
    settings = get_settings()
    return RootResponse(
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Explainable CI/CD Failure Diagnosis & Temporal Correlation Engine",
        docs_url="/docs",
        health_url="/health",
    )
