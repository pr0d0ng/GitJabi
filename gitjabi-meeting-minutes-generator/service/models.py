from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SourcePayload(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    site_id: str = Field(..., min_length=1)
    drive_item_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    web_url: str | None = None
    last_modified: str | None = None
    download_url: str = Field(..., min_length=1)


class OptionsPayload(BaseModel):
    blob_prefix: str = "meeting-minutes"
    key_limit: int = 180
    action_limit: int = 120
    other_sample_limit: int = 20
    max_prompt_chars: int = 18000
    min_key_retain: int = 40
    min_action_retain: int = 20
    stt_chunk_minutes: int = 0


class JobRequest(BaseModel):
    source: SourcePayload
    options: OptionsPayload = OptionsPayload()
    idempotency_key: str = Field(..., min_length=1)


class JobResponse(BaseModel):
    job_id: str
    status: str
    duplicate_of: str | None = None


class JobStatus(BaseModel):
    job_id: str
    idempotency_key: str
    status: str
    source_name: str
    created_at: datetime
    updated_at: datetime
    result: dict[str, Any] | None = None
    error: str | None = None
