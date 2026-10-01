from __future__ import annotations

import logging
import os
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from pydantic import ValidationError

from service.models import JobRequest
from service.queueing import QueueMessage, create_job_queue
from service.state import create_job_store
from service.worker import run_job

logging.basicConfig(level=os.getenv("WORKER_LOG_LEVEL", "INFO"))
log = logging.getLogger("worker-loop")


def _process_job(job_id: str, payload_dict: dict) -> None:
    store = create_job_store()
    store.set_running(job_id)
    try:
        payload = JobRequest.model_validate(payload_dict)
        result = run_job(payload)
        store.set_done(job_id, result=result)
        log.info("job done job_id=%s", job_id)
    except ValidationError as exc:
        store.set_failed(job_id, error=f"payload_validation_error: {exc}")
        log.exception("payload validation failed job_id=%s", job_id)
    except Exception as exc:  # noqa: BLE001
        store.set_failed(job_id, error=str(exc))
        log.exception("job failed job_id=%s", job_id)


def run() -> None:
    queue = create_job_queue()
    if not queue:
        raise RuntimeError("Missing queue config. Set BLOB_CONNECTION_STRING and JOB_QUEUE_NAME.")

    concurrency = int(os.getenv("WORKER_MAX_CONCURRENCY", "1"))
    poll_interval = float(os.getenv("WORKER_POLL_INTERVAL_SEC", "5"))
    log.info("worker loop started concurrency=%d queue=%s", concurrency, os.getenv("JOB_QUEUE_NAME"))

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        inflight = set()
        while True:
            while len(inflight) < concurrency:
                msgs = queue.receive_batch(max_messages=1, visibility_timeout=3600)
                if not msgs:
                    break
                msg = msgs[0]
                decoded = QueueMessage.from_json(msg.content)
                fut = ex.submit(_process_job, decoded.job_id, decoded.payload)
                fut._queue_msg = msg  # type: ignore[attr-defined]
                inflight.add(fut)
                log.info("job dequeued job_id=%s inflight=%d", decoded.job_id, len(inflight))

            if not inflight:
                time.sleep(poll_interval)
                continue

            done, _ = wait(inflight, timeout=1, return_when=FIRST_COMPLETED)
            for fut in done:
                inflight.remove(fut)
                msg = getattr(fut, "_queue_msg", None)
                if msg is not None:
                    try:
                        queue.delete(msg)
                    except Exception:
                        log.exception("failed to delete queue message")


if __name__ == "__main__":
    run()
