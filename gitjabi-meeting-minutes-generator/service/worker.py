from __future__ import annotations

import time
import subprocess
import sys
import os
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import requests

from service.models import JobRequest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    v = value.strip()
    if v.endswith("Z"):
        v = v.replace("Z", "+00:00")
    return datetime.fromisoformat(v)


def _build_output_stem(last_modified: str | None) -> str:
    dt = _parse_dt(last_modified)
    return dt.astimezone(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _download_source_file(payload: JobRequest, download_dir: Path) -> tuple[Path, str]:
    source = payload.source
    output_stem = _build_output_stem(source.last_modified)
    local_path = download_dir / f"{output_stem}.mp4"
    download_dir.mkdir(parents=True, exist_ok=True)

    download_url = source.download_url
    with requests.get(download_url, stream=True, timeout=300) as resp:
        if resp.status_code == 401:
            refreshed = _refresh_graph_download_url(payload)
            if refreshed:
                download_url = refreshed
                resp = requests.get(download_url, stream=True, timeout=300)
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    return local_path, output_stem


def _refresh_graph_download_url(payload: JobRequest) -> str | None:
    tenant_id = os.getenv("TENANT_ID", "").strip()
    client_id = os.getenv("CLIENT_ID", "").strip()
    client_secret = os.getenv("CLIENT_SECRET", "").strip()
    if not tenant_id or not client_id or not client_secret:
        return None

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    token_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    token_resp = requests.post(token_url, data=token_data, timeout=30)
    token_resp.raise_for_status()
    token = token_resp.json()["access_token"]

    source = payload.source
    item_url = (
        f"https://graph.microsoft.com/v1.0/sites/{source.site_id}/drive/items/{source.drive_item_id}"
        "?$select=id,name,@microsoft.graph.downloadUrl"
    )
    item_resp = requests.get(item_url, headers={"Authorization": f"Bearer {token}"}, timeout=60)
    item_resp.raise_for_status()
    item = item_resp.json()
    return item.get("@microsoft.graph.downloadUrl")


def run_job(payload: JobRequest) -> dict:
    timings: dict[str, float] = {}
    t0 = time.perf_counter()
    download_dir = PROJECT_ROOT / "temp" / "service_jobs"
    print(f"[worker] start source={payload.source.name}")
    s0 = time.perf_counter()
    local_media_path, output_stem = _download_source_file(payload, download_dir)
    timings["download_source_file"] = round(time.perf_counter() - s0, 3)
    print(f"[worker] downloaded media={local_media_path} sec={timings['download_source_file']}")

    options = payload.options
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "meeting_minutes_pipeline.py"),
        "--media",
        str(local_media_path),
        "--output-stem",
        output_stem,
        "--meeting-datetime",
        str(payload.source.last_modified or ""),
        "--blob-prefix",
        options.blob_prefix,
        "--key-limit",
        str(options.key_limit),
        "--action-limit",
        str(options.action_limit),
        "--other-sample-limit",
        str(options.other_sample_limit),
        "--max-prompt-chars",
        str(options.max_prompt_chars),
        "--min-key-retain",
        str(options.min_key_retain),
        "--min-action-retain",
        str(options.min_action_retain),
    ]
    if int(options.stt_chunk_minutes or 0) > 0:
        cmd.extend(["--stt-chunk-minutes", str(options.stt_chunk_minutes)])
    s0 = time.perf_counter()
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    output_tail: deque[str] = deque(maxlen=80)
    assert proc.stdout is not None
    for line in proc.stdout:
        text = line.rstrip("\n")
        print(text, flush=True)
        output_tail.append(text)
    proc.wait()
    timings["meeting_minutes_pipeline"] = round(time.perf_counter() - s0, 3)
    if int(proc.returncode or 0) != 0:
        output_tail_text = "\n".join(output_tail)
        raise RuntimeError(
            "meeting_minutes_pipeline failed "
            f"(exit={proc.returncode}).\n"
            f"--- output_tail ---\n{output_tail_text}"
        )
    timings["total"] = round(time.perf_counter() - t0, 3)
    print(
        "[worker] done",
        f"output_stem={output_stem}",
        f"pipeline_sec={timings['meeting_minutes_pipeline']}",
        f"total_sec={timings['total']}",
    )

    return {
        "output_stem": output_stem,
        "source_name": payload.source.name,
        "blob_prefix": options.blob_prefix,
        "local_media_path": str(local_media_path),
        "timings_sec": timings,
    }
