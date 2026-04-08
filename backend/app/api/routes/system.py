from fastapi import APIRouter

from backend.app.core.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/health", summary="Service health check")
def health_check() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


@router.get("/version", summary="Service version")
def version() -> dict[str, str]:
    settings = get_settings()
    return {
        "service": settings.app_name,
        "version": settings.app_version,
    }
