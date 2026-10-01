from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import azure.functions as func
import requests
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
USER_AGENT = "meeting-doc-poller/1.0"

app = func.FunctionApp()
TIMER_SCHEDULE = os.getenv("POLLER_TIMER_SCHEDULE", "0 */50 * * * *")


@dataclass
class PollTarget:
    tenant_id: str
    domain: str
    site_name: str
    site_path: str
    folder_path: str
    enabled: bool = True


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    return datetime.fromisoformat(v)


def get_access_token() -> str:
    tenant_id = os.getenv("TENANT_ID", "").strip()
    client_id = os.getenv("CLIENT_ID", "").strip()
    client_secret = os.getenv("CLIENT_SECRET", "").strip()
    if not tenant_id or not client_id or not client_secret:
        raise RuntimeError("Missing TENANT_ID / CLIENT_ID / CLIENT_SECRET")

    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    resp = requests.post(url, data=data, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def _graph_get(url: str, token: str) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    resp = requests.get(url, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()


def _resolve_site_id(token: str, domain: str, site_name: str, site_path: str) -> str:
    candidates: list[str] = []
    if site_path:
        normalized_path = site_path if site_path.startswith("/") else f"/{site_path}"
        candidates.append(normalized_path)
    candidates.extend([f"/sites/{site_name}", f"/teams/{site_name}"])

    for path in candidates:
        encoded = quote(path, safe="/-_.")
        for suffix in ("", ":"):
            url = f"{GRAPH_BASE_URL}/sites/{domain}:{encoded}{suffix}"
            try:
                payload = _graph_get(url, token)
                site_id = payload.get("id")
                if site_id:
                    return site_id
            except requests.HTTPError:
                continue

    search_url = f"{GRAPH_BASE_URL}/sites?search={quote(site_name)}"
    payload = _graph_get(search_url, token)
    for site in payload.get("value", []):
        web_url = str(site.get("webUrl", ""))
        if domain in web_url and f"/{site_name}" in web_url and site.get("id"):
            return site["id"]

    raise RuntimeError(
        f"Could not resolve site id for domain={domain}, site_name={site_name}, site_path={site_path}"
    )


def _iter_files(token: str, site_id: str, folder_path: str):
    encoded_path = quote(folder_path, safe="/-_.() ")
    next_url = f"{GRAPH_BASE_URL}/sites/{site_id}/drive/root:/{encoded_path}:/children"
    while next_url:
        payload = _graph_get(next_url, token)
        for item in payload.get("value", []):
            if "file" in item:
                yield item
            elif "folder" in item:
                parent_path = item.get("parentReference", {}).get("path", "")
                parent_path = parent_path.split("root:", 1)[-1].strip("/")
                child_path = f"{parent_path}/{item['name']}".strip("/")
                yield from _iter_files(token, site_id, child_path)
        next_url = payload.get("@odata.nextLink")


def _load_targets(default_tenant_id: str) -> list[PollTarget]:
    raw = (os.getenv("POLLER_TARGETS_JSON") or "").strip()
    if raw:
        data = json.loads(raw)
        targets: list[PollTarget] = []
        for row in data:
            targets.append(
                PollTarget(
                    tenant_id=str(row.get("tenant_id") or default_tenant_id),
                    domain=str(row["domain"]),
                    site_name=str(row["site_name"]),
                    site_path=str(row.get("site_path") or ""),
                    folder_path=str(row["folder_path"]),
                    enabled=bool(row.get("enabled", True)),
                )
            )
        return [t for t in targets if t.enabled]

    return [
        PollTarget(
            tenant_id=default_tenant_id,
            domain=os.getenv("SHAREPOINT_DOMAIN", "elixirrkc.sharepoint.com"),
            site_name=os.getenv("SHAREPOINT_SITE_NAME", ""),
            site_path=os.getenv("SHAREPOINT_SITE_PATH", ""),
            folder_path=os.getenv("SHAREPOINT_FOLDER_PATH", "Shared Documents"),
            enabled=True,
        )
    ]


def _load_state_from_blob() -> dict[str, Any]:
    conn = os.getenv("BLOB_CONNECTION_STRING", "")
    container_name = os.getenv("POLLER_STATE_CONTAINER", "meeting-automation-state")
    blob_name = os.getenv("POLLER_STATE_BLOB", "processed_items.json")
    if not conn:
        return {"processed": {}}

    service = BlobServiceClient.from_connection_string(conn)
    container = service.get_container_client(container_name)
    try:
        container.create_container()
    except Exception:
        pass

    blob_client = container.get_blob_client(blob_name)
    try:
        data = blob_client.download_blob().readall()
        return json.loads(data.decode("utf-8"))
    except Exception:
        return {"processed": {}}


def _save_state_to_blob(state: dict[str, Any]) -> None:
    conn = os.getenv("BLOB_CONNECTION_STRING", "")
    if not conn:
        return
    container_name = os.getenv("POLLER_STATE_CONTAINER", "meeting-automation-state")
    blob_name = os.getenv("POLLER_STATE_BLOB", "processed_items.json")
    service = BlobServiceClient.from_connection_string(conn)
    container = service.get_container_client(container_name)
    try:
        container.create_container()
    except Exception:
        pass
    payload = json.dumps(state, ensure_ascii=False).encode("utf-8")
    container.upload_blob(blob_name, payload, overwrite=True)


def _trim_state(state: dict[str, Any], max_items: int = 10000) -> None:
    processed = state.setdefault("processed", {})
    if len(processed) <= max_items:
        return
    pairs = sorted(processed.items(), key=lambda x: x[1], reverse=True)
    state["processed"] = dict(pairs[:max_items])


def _build_idempotency_key(tenant_id: str, site_id: str, item: dict[str, Any]) -> str:
    item_id = item.get("id") or ""
    etag = item.get("eTag") or item.get("cTag") or item.get("lastModifiedDateTime") or "na"
    return f"{tenant_id}:{site_id}:{item_id}:{etag}"


def _post_job(api_base_url: str, api_key: str, payload: dict[str, Any]) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-Internal-Key"] = api_key
    resp = requests.post(
        f"{api_base_url.rstrip('/')}/jobs/meeting-minutes",
        json=payload,
        headers=headers,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def _should_include(item: dict[str, Any], lookback_hours: int) -> bool:
    if lookback_hours <= 0:
        return True
    ts = item.get("lastModifiedDateTime") or item.get("createdDateTime")
    dt = _parse_dt(ts)
    threshold = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    return dt >= threshold


@app.timer_trigger(schedule=TIMER_SCHEDULE, arg_name="timer", run_on_startup=False, use_monitor=True)
def poll_teams_recordings(timer: func.TimerRequest) -> None:
    logging.info("Timer fired. past_due=%s", timer.past_due)

    api_base_url = (os.getenv("MEETING_API_BASE_URL") or "").strip()
    if not api_base_url:
        logging.error("Missing MEETING_API_BASE_URL; skipping run.")
        return

    api_key = (os.getenv("MEETING_API_KEY") or "").strip()
    options = {
        "blob_prefix": os.getenv("POLLER_BLOB_PREFIX", "meeting-minutes"),
        "key_limit": int(os.getenv("POLLER_KEY_LIMIT", "180")),
        "action_limit": int(os.getenv("POLLER_ACTION_LIMIT", "120")),
        "other_sample_limit": int(os.getenv("POLLER_OTHER_SAMPLE_LIMIT", "20")),
        "max_prompt_chars": int(os.getenv("POLLER_MAX_PROMPT_CHARS", "18000")),
        "min_key_retain": int(os.getenv("POLLER_MIN_KEY_RETAIN", "40")),
        "min_action_retain": int(os.getenv("POLLER_MIN_ACTION_RETAIN", "20")),
        "stt_chunk_minutes": int(os.getenv("POLLER_STT_CHUNK_MINUTES", "0")),
    }
    lookback_hours = int(os.getenv("POLLER_LOOKBACK_HOURS", "72"))
    max_items_per_run = int(os.getenv("POLLER_MAX_ITEMS_PER_RUN", "1"))

    token = get_access_token()
    state = _load_state_from_blob()
    processed: dict[str, str] = state.setdefault("processed", {})

    default_tenant_id = os.getenv("TENANT_ID", "unknown-tenant")
    targets = _load_targets(default_tenant_id=default_tenant_id)
    queued = 0
    skipped_known = 0

    for target in targets:
        if not target.site_name:
            logging.warning("Skipping target with empty site_name: %s", target)
            continue
        try:
            site_id = _resolve_site_id(
                token=token,
                domain=target.domain,
                site_name=target.site_name,
                site_path=target.site_path,
            )
            logging.info("Resolved site_id=%s for %s/%s", site_id, target.domain, target.site_name)
        except Exception:
            logging.exception("Failed to resolve site id for target=%s", target)
            continue

        try:
            files = list(_iter_files(token, site_id, target.folder_path))
        except Exception:
            logging.exception("Failed to list files for target=%s site_id=%s", target, site_id)
            continue

        mp4_items = [
            x
            for x in files
            if str(x.get("name", "")).lower().endswith(".mp4")
            and x.get("@microsoft.graph.downloadUrl")
            and _should_include(x, lookback_hours)
        ]
        mp4_items.sort(key=lambda x: _parse_dt(x.get("lastModifiedDateTime") or x.get("createdDateTime")), reverse=True)
        if max_items_per_run > 0:
            mp4_items = mp4_items[:max_items_per_run]
        logging.info(
            "Target %s/%s folder=%s mp4_candidates=%d queued_limit=%d",
            target.domain,
            target.site_name,
            target.folder_path,
            len(mp4_items),
            max_items_per_run,
        )

        for item in mp4_items:
            idem = _build_idempotency_key(target.tenant_id, site_id, item)
            if idem in processed:
                skipped_known += 1
                continue

            last_modified = item.get("lastModifiedDateTime") or item.get("createdDateTime") or ""
            payload = {
                "source": {
                    "tenant_id": target.tenant_id,
                    "site_id": site_id,
                    "drive_item_id": item.get("id", ""),
                    "name": item.get("name", ""),
                    "web_url": item.get("webUrl"),
                    "last_modified": last_modified,
                    "download_url": item.get("@microsoft.graph.downloadUrl"),
                },
                "options": options,
                "idempotency_key": idem,
            }
            try:
                response = _post_job(api_base_url, api_key, payload)
                queued += 1
                processed[idem] = datetime.now(timezone.utc).isoformat()
                logging.info(
                    "Queued item name=%s job_id=%s status=%s",
                    item.get("name"),
                    response.get("job_id"),
                    response.get("status"),
                )
            except Exception:
                logging.exception("Failed to queue job for file=%s", item.get("name"))

    _trim_state(state)
    _save_state_to_blob(state)
    logging.info("Poll complete. queued=%d skipped_known=%d state_size=%d", queued, skipped_known, len(processed))

