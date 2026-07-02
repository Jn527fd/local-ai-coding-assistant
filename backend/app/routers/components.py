from typing import Any

from fastapi import APIRouter, Depends, Request

from app.auth.user_session import require_user_session
from app.services.component_registry import ComponentRegistry

router = APIRouter(
    prefix="/components",
    tags=["components"],
    dependencies=[Depends(require_user_session)],
)


@router.get("/capabilities")
async def component_capabilities(
    request: Request,
) -> dict[str, list[dict[str, Any]]]:
    """Return discovered local AI component capabilities."""

    registry: ComponentRegistry = request.app.state.component_registry
    return await registry.capabilities()
