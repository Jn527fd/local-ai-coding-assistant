from typing import Any

from fastapi import APIRouter, Depends, Request

from app.auth.api_key import require_session_or_api_key
from app.services.diagnostics import DiagnosticsService

router = APIRouter(
    prefix="/diagnostics",
    tags=["diagnostics"],
    dependencies=[Depends(require_session_or_api_key)],
)


def get_diagnostics_service(request: Request) -> DiagnosticsService:
    return request.app.state.diagnostics_service


@router.get("/status")
async def diagnostics_status(
    diagnostics_service: DiagnosticsService = Depends(get_diagnostics_service),
) -> dict[str, Any]:
    return await diagnostics_service.status()


@router.get("/support-bundle")
async def support_bundle(
    diagnostics_service: DiagnosticsService = Depends(get_diagnostics_service),
) -> dict[str, Any]:
    return await diagnostics_service.support_bundle()
