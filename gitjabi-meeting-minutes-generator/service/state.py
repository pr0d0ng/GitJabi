from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from threading import Lock

from azure.storage.blob import BlobServiceClient

from service.models import JobRequest, JobStatus


class JobStore:
    def get_job_id_by_idempotency(self, key: str) -> str | None:  # pragma: no cover - interface
        raise NotImplementedError

    def create_job(self, job_id: str, payload: JobRequest) -> JobStatus:  # pragma: no cover - interface
        raise NotImplementedError

    def set_running(self, job_id: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def set_done(self, job_id: str, result: dict) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def set_failed(self, job_id: str, error: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def get_job(self, job_id: str) -> JobStatus | None:  # pragma: no cover - interface
        raise NotImplementedError


class InMemoryJobStore(JobStore):
    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs_by_id: dict[str, JobStatus] = {}
        self._job_id_by_idempotency: dict[str, str] = {}

    def get_job_id_by_idempotency(self, key: str) -> str | None:
        with self._lock:
            return self._job_id_by_idempotency.get(key)

    def create_job(self, job_id: str, payload: JobRequest) -> JobStatus:
        now = datetime.now(timezone.utc)
        status = JobStatus(
            job_id=job_id,
            idempotency_key=payload.idempotency_key,
            status="accepted",
            source_name=payload.source.name,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._jobs_by_id[job_id] = status
            self._job_id_by_idempotency[payload.idempotency_key] = job_id
        return status

    def set_running(self, job_id: str) -> None:
        self._update(job_id, status="running")

    def set_done(self, job_id: str, result: dict) -> None:
        self._update(job_id, status="done", result=result, error=None)

    def set_failed(self, job_id: str, error: str) -> None:
        self._update(job_id, status="failed", error=error)

    def get_job(self, job_id: str) -> JobStatus | None:
        with self._lock:
            return self._jobs_by_id.get(job_id)

    def _update(self, job_id: str, **kwargs) -> None:
        with self._lock:
            current = self._jobs_by_id.get(job_id)
            if not current:
                return
            data = current.model_dump()
            data.update(kwargs)
            data["updated_at"] = datetime.now(timezone.utc)
            self._jobs_by_id[job_id] = JobStatus(**data)


class BlobJobStore(JobStore):
    def __init__(self, conn: str, container: str = "meeting-automation-state", prefix: str = "job-store") -> None:
        self._lock = Lock()
        self._svc = BlobServiceClient.from_connection_string(conn)
        self._container = self._svc.get_container_client(container)
        self._prefix = prefix.strip("/")
        try:
            self._container.create_container()
        except Exception:
            pass

    def _job_blob(self, job_id: str) -> str:
        return f"{self._prefix}/jobs/{job_id}.json"

    def _idem_hash(self, key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _idem_blob(self, idem_key: str) -> str:
        return f"{self._prefix}/idem/{self._idem_hash(idem_key)}.txt"

    def _read_text(self, blob_name: str) -> str | None:
        blob = self._container.get_blob_client(blob_name)
        try:
            return blob.download_blob().readall().decode("utf-8")
        except Exception:
            return None

    def _write_text(self, blob_name: str, text: str) -> None:
        self._container.upload_blob(blob_name, text.encode("utf-8"), overwrite=True)

    def _read_job(self, job_id: str) -> JobStatus | None:
        raw = self._read_text(self._job_blob(job_id))
        if not raw:
            return None
        try:
            return JobStatus.model_validate(json.loads(raw))
        except Exception:
            return None

    def _write_job(self, job: JobStatus) -> None:
        payload = json.dumps(job.model_dump(mode="json"), ensure_ascii=False)
        self._write_text(self._job_blob(job.job_id), payload)

    def get_job_id_by_idempotency(self, key: str) -> str | None:
        return self._read_text(self._idem_blob(key))

    def create_job(self, job_id: str, payload: JobRequest) -> JobStatus:
        now = datetime.now(timezone.utc)
        status = JobStatus(
            job_id=job_id,
            idempotency_key=payload.idempotency_key,
            status="accepted",
            source_name=payload.source.name,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._write_job(status)
            self._write_text(self._idem_blob(payload.idempotency_key), job_id)
        return status

    def set_running(self, job_id: str) -> None:
        self._update(job_id, status="running")

    def set_done(self, job_id: str, result: dict) -> None:
        self._update(job_id, status="done", result=result, error=None)

    def set_failed(self, job_id: str, error: str) -> None:
        self._update(job_id, status="failed", error=error)

    def get_job(self, job_id: str) -> JobStatus | None:
        return self._read_job(job_id)

    def _update(self, job_id: str, **kwargs) -> None:
        with self._lock:
            current = self._read_job(job_id)
            if not current:
                return
            data = current.model_dump()
            data.update(kwargs)
            data["updated_at"] = datetime.now(timezone.utc)
            self._write_job(JobStatus(**data))


def create_job_store() -> JobStore:
    conn = os.getenv("BLOB_CONNECTION_STRING", "").strip()
    if not conn:
        return InMemoryJobStore()
    container = os.getenv("JOB_STORE_CONTAINER", "meeting-automation-state")
    prefix = os.getenv("JOB_STORE_PREFIX", "job-store")
    return BlobJobStore(conn=conn, container=container, prefix=prefix)
