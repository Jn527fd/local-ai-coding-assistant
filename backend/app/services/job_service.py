from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

from app.metadata import MetadataStore
from app.schemas.jobs import JobRecord

JobRunner = Callable[["JobContext"], Awaitable[dict[str, Any]]]

TERMINAL_STATES = {"succeeded", "failed", "cancelled"}


class JobServiceError(Exception):
    """Base error for local background jobs."""


class JobNotFoundError(JobServiceError):
    """Raised when a requested job is not known locally."""


class JobCancelledError(JobServiceError):
    """Raised by a job runner when cancellation is requested at a safe point."""


class JobContext:
    """Progress and cancellation handle passed to job runners."""

    def __init__(self, service: "JobService", job_id: str) -> None:
        self.service = service
        self.job_id = job_id

    async def progress(self, percent: int, message: str) -> None:
        self.service.update_progress(self.job_id, percent, message)
        await asyncio.sleep(0)

    def check_cancelled(self) -> None:
        if self.service.cancel_requested(self.job_id):
            raise JobCancelledError("Job cancellation was requested.")


class JobService:
    """Small in-process job runner with SQLite-backed job metadata."""

    def __init__(self, metadata_store: MetadataStore) -> None:
        self.metadata_store = metadata_store
        self._lock = Lock()
        self._jobs: dict[str, dict[str, Any]] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def create(
        self,
        job_type: str,
        runner: JobRunner,
        *,
        target_type: str | None = None,
        target_id: str | None = None,
        payload: dict[str, Any] | None = None,
        message: str = "Queued.",
    ) -> JobRecord:
        now = self._now()
        job = {
            "id": uuid4().hex,
            "type": job_type,
            "state": "queued",
            "progress": 0,
            "message": message,
            "targetType": target_type,
            "targetId": target_id,
            "payload": payload or {},
            "result": None,
            "error": None,
            "cancelRequested": False,
            "createdAt": now,
            "updatedAt": now,
            "startedAt": None,
            "finishedAt": None,
        }
        with self._lock:
            self._jobs[job["id"]] = job
        self._persist(job)
        task = asyncio.create_task(self._run(job["id"], runner))
        with self._lock:
            self._tasks[job["id"]] = task
        return self._record(job)

    def get(self, job_id: str) -> JobRecord:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            stored = self.metadata_store.get_job(job_id)
            if stored is None:
                raise JobNotFoundError("Job was not found.")
            job = stored
            with self._lock:
                self._jobs[job_id] = job
        return self._record(job)

    def list(self, limit: int = 50) -> list[JobRecord]:
        return [
            self._record(job)
            for job in self.metadata_store.list_jobs(limit=limit)
        ]

    def cancel(self, job_id: str) -> JobRecord:
        job = self._mutable_job(job_id)
        if job["state"] in TERMINAL_STATES:
            return self._record(job)
        self._update(
            job_id,
            state="cancel_requested",
            cancelRequested=True,
            message="Cancellation requested.",
        )
        return self.get(job_id)

    def cancel_requested(self, job_id: str) -> bool:
        try:
            return self.get(job_id).cancelRequested
        except JobNotFoundError:
            return False

    def update_progress(self, job_id: str, percent: int, message: str) -> None:
        job = self._mutable_job(job_id)
        if job["state"] in TERMINAL_STATES:
            return
        state = "cancel_requested" if job.get("cancelRequested") else "running"
        self._update(
            job_id,
            state=state,
            progress=max(0, min(99, percent)),
            message=message,
        )

    async def _run(self, job_id: str, runner: JobRunner) -> None:
        try:
            job = self._mutable_job(job_id)
            if job.get("cancelRequested"):
                raise JobCancelledError("Job was cancelled before it started.")
            self._update(
                job_id,
                state="running",
                progress=max(1, int(job.get("progress") or 0)),
                message="Running.",
                startedAt=self._now(),
            )
            result = await runner(JobContext(self, job_id))
            self._update(
                job_id,
                state="succeeded",
                progress=100,
                message="Completed.",
                result=result,
                finishedAt=self._now(),
            )
        except JobCancelledError as exc:
            self._update(
                job_id,
                state="cancelled",
                message=str(exc),
                error=None,
                finishedAt=self._now(),
            )
        except Exception as exc:
            self._update(
                job_id,
                state="failed",
                message="Failed.",
                error=str(exc),
                finishedAt=self._now(),
            )
        finally:
            with self._lock:
                self._tasks.pop(job_id, None)

    def _mutable_job(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            stored = self.metadata_store.get_job(job_id)
            if stored is None:
                raise JobNotFoundError("Job was not found.")
            job = stored
            with self._lock:
                self._jobs[job_id] = job
        return job

    def _update(self, job_id: str, **patch: Any) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.update(patch)
            job["updatedAt"] = self._now()
            snapshot = dict(job)
        self._persist(snapshot)

    def _persist(self, job: dict[str, Any]) -> None:
        self.metadata_store.upsert_job(job)

    @staticmethod
    def _record(job: dict[str, Any]) -> JobRecord:
        return JobRecord.model_validate(job)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
