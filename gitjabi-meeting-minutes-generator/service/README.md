# AKS Meeting Minutes API

Minimal API for Step 1 of `AZURE_FUNCTIONS_AKS_PLAN.md`.

## Endpoints

- `GET /healthz`
- `POST /jobs/meeting-minutes`
- `GET /jobs/{job_id}`

## Run (from project root)

```powershell
python -m uvicorn service.api:app --host 0.0.0.0 --port 8080
```

## Request example

```json
{
  "source": {
    "tenant_id": "tenant-1",
    "site_id": "site-1",
    "drive_item_id": "drive-item-1",
    "name": "meeting.mp4",
    "web_url": "https://example.sharepoint.com/...",
    "last_modified": "2026-02-19T08:27:58Z",
    "download_url": "https://graph-download-url"
  },
  "options": {
    "blob_prefix": "meeting-minutes",
    "key_limit": 180,
    "action_limit": 120,
    "other_sample_limit": 20,
    "max_prompt_chars": 18000
  },
  "idempotency_key": "tenant-1:site-1:drive-item-1:2026-02-19T08:27:58Z"
}
```

## Notes

- If `BLOB_CONNECTION_STRING` is set, job status is persisted to Blob (`JOB_STORE_CONTAINER/JOB_STORE_PREFIX`).
- If `JOB_QUEUE_NAME` is set, API enqueues jobs to Azure Queue.
- Run worker loop separately:

```powershell
python -m service.worker_loop
```

- Worker consumes queue and executes `meeting_minutes_pipeline.py`.
- For long recordings, set `POLLER_STT_CHUNK_MINUTES` (e.g. `20`) to split STT input into chunks.
