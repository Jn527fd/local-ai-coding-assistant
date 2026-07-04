import asyncio
import time

import pytest

from app.metadata import MetadataStore
from app.services.job_service import JobCancelledError, JobService
from tests.test_vector_indexes import (
    configure_vector_tests,
    upload_document,
)


async def _successful_runner(context):
    await context.progress(25, "working")
    context.check_cancelled()
    return {"ok": True}


async def _cancelled_runner(context):
    await context.progress(10, "checking")
    context.check_cancelled()
    raise AssertionError("runner should have cancelled")


def _wait_for_job(client, auth_headers, job_id: str, timeout: float = 3.0):
    deadline = time.time() + timeout
    payload = None
    while time.time() < deadline:
        response = client.get(f"/jobs/{job_id}", headers=auth_headers)
        assert response.status_code == 200
        payload = response.json()["job"]
        if payload["state"] in {"succeeded", "failed", "cancelled"}:
            return payload
        time.sleep(0.05)
    return payload


@pytest.mark.anyio
async def test_job_service_tracks_successful_state(tmp_path):
    store = MetadataStore(tmp_path / "metadata.sqlite3")
    with store.connect() as connection:
        with connection:
            store.apply_schema_v2(connection)
    service = JobService(store)

    job = service.create("test.success", _successful_runner)
    deadline = time.time() + 3.0
    while time.time() < deadline:
        current = service.get(job.id)
        if current.state == "succeeded":
            break
        await asyncio.sleep(0.05)

    current = service.get(job.id)
    assert current.state == "succeeded"
    assert current.progress == 100
    assert current.result == {"ok": True}
    assert store.get_job(job.id)["state"] == "succeeded"


@pytest.mark.anyio
async def test_job_service_cancels_at_safe_point(tmp_path):
    store = MetadataStore(tmp_path / "metadata.sqlite3")
    with store.connect() as connection:
        with connection:
            store.apply_schema_v2(connection)
    service = JobService(store)

    job = service.create("test.cancel", _cancelled_runner)
    service.cancel(job.id)
    deadline = time.time() + 3.0
    while time.time() < deadline:
        current = service.get(job.id)
        if current.state == "cancelled":
            break
        await asyncio.sleep(0.05)

    assert service.get(job.id).state == "cancelled"


def test_job_status_api_requires_api_key(client):
    response = client.get("/jobs/missing")

    assert response.status_code == 401


def test_document_process_job_completes(
    app,
    client,
    auth_headers,
    tmp_path,
):
    configure_vector_tests(app, tmp_path)
    document = upload_document(client, auth_headers, "conversation-a", b"apple")

    response = client.post(
        f"/documents/{document['documentId']}/process/jobs",
        headers=auth_headers,
        json={
            "conversationId": "conversation-a",
            "conversationSettings": {
                "embedderModel": "embed-a",
                "chunker": "fixed",
            },
        },
    )

    assert response.status_code == 202
    payload = _wait_for_job(client, auth_headers, response.json()["job"]["id"])
    assert payload["state"] == "succeeded"
    assert payload["progress"] == 100
    assert payload["result"]["status"] == "processed"


def test_document_index_job_completes(
    app,
    client,
    auth_headers,
    tmp_path,
):
    configure_vector_tests(app, tmp_path)
    document = upload_document(client, auth_headers, "conversation-a", b"apple")
    process_response = client.post(
        f"/documents/{document['documentId']}/process",
        headers=auth_headers,
        json={
            "conversationId": "conversation-a",
            "conversationSettings": {
                "embedderModel": "embed-a",
                "chunker": "fixed",
            },
        },
    )
    assert process_response.status_code == 200

    response = client.post(
        f"/documents/{document['documentId']}/index/jobs",
        headers=auth_headers,
        json={
            "conversationId": "conversation-a",
            "conversationSettings": {
                "embedderModel": "embed-a",
                "chunker": "fixed",
                "vectorDatabase": "chroma",
            },
        },
    )

    assert response.status_code == 202
    payload = _wait_for_job(client, auth_headers, response.json()["job"]["id"])
    assert payload["state"] == "succeeded"
    assert payload["result"]["indexedChunks"] == 1


def test_cancel_document_job_is_conservative(client, auth_headers):
    response = client.post("/jobs/not-real/cancel", headers=auth_headers)

    assert response.status_code == 404
