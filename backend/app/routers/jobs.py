from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.auth.api_key import require_api_key
from app.schemas.jobs import JobListResponse, JobResponse
from app.services.job_service import JobNotFoundError, JobService

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
    dependencies=[Depends(require_api_key)],
)


def get_job_service(request: Request) -> JobService:
    return request.app.state.job_service


def raise_job_http_error(error: Exception) -> None:
    if isinstance(error, JobNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    raise error


@router.get("", response_model=JobListResponse)
async def list_jobs(
    job_service: Annotated[JobService, Depends(get_job_service)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> JobListResponse:
    return JobListResponse(jobs=job_service.list(limit=limit))


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> JobResponse:
    try:
        return JobResponse(job=job_service.get(job_id))
    except JobNotFoundError as exc:
        raise_job_http_error(exc)


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: str,
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> JobResponse:
    try:
        return JobResponse(job=job_service.cancel(job_id))
    except JobNotFoundError as exc:
        raise_job_http_error(exc)
