from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException

from service.models import JobRequest, JobResponse
from service.queueing import QueueMessage, create_job_queue
from service.state import create_job_store
from service.worker import run_job

app = FastAPI(title="Meeting Minutes Service", version="0.1.0")
store = create_job_store()
job_queue = create_job_queue()
INTERNAL_API_KEY = os.getenv("MEETING_API_KEY", "").strip()
WORKER_MAX_CONCURRENCY = int(os.getenv("WORKER_MAX_CONCURRENCY", "1"))
executor = ThreadPoolExecutor(max_workers=WORKER_MAX_CONCURRENCY)


def _run_job_background(job_id: str, payload: JobRequest) -> None:
    store.set_running(job_id)
    try:
        result = run_job(payload)
        store.set_done(job_id, result=result)
    except Exception as exc:  # noqa: BLE001
        store.set_failed(job_id, error=str(exc))


@app.on_event("shutdown")
def _shutdown_executor() -> None:
    executor.shutdown(wait=False, cancel_futures=True)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/jobs/meeting-minutes", response_model=JobResponse)
def create_meeting_minutes_job(
    payload: JobRequest,
    x_internal_key: str | None = Header(default=None),
) -> JobResponse:
    if INTERNAL_API_KEY and x_internal_key != INTERNAL_API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")

    existing = store.get_job_id_by_idempotency(payload.idempotency_key)
    if existing:
        return JobResponse(job_id=existing, status="duplicate", duplicate_of=existing)

    job_id = str(uuid4())
    store.create_job(job_id, payload)
    if job_queue:
        job_queue.enqueue(QueueMessage(job_id=job_id, payload=payload.model_dump(mode="json")))
    else:
        executor.submit(_run_job_background, job_id, payload)
    return JobResponse(job_id=job_id, status="accepted")


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job_not_found")
    return job.model_dump(mode="json")
