from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.user_session import require_user_session
from app.schemas.models import (
    ModelStatusResponse,
    ModelSwitchRequest,
    ModelSwitchResponse,
)
from app.services.model_manager import (
    ModelManager,
    ModelSwitchInProgressError,
    UnsupportedModelError,
)
from app.services.ollama_service import OllamaServiceError

router = APIRouter(
    prefix="/models",
    tags=["models"],
    dependencies=[Depends(require_user_session)],
)


@router.get("/status", response_model=ModelStatusResponse)
async def model_status(request: Request) -> ModelStatusResponse:
    manager: ModelManager = request.app.state.model_manager
    return ModelStatusResponse.model_validate(await manager.status())


@router.post(
    "/switch",
    response_model=ModelSwitchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def switch_model(
    switch_request: ModelSwitchRequest,
    request: Request,
) -> ModelSwitchResponse:
    manager: ModelManager = request.app.state.model_manager
    try:
        await manager.start_switch(switch_request.model)
    except UnsupportedModelError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ModelSwitchInProgressError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except OllamaServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return ModelSwitchResponse(accepted=True, model=switch_request.model)
