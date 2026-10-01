import base64
import json
import os
from typing import Iterable
from urllib.parse import quote

import requests
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
SITE_NAME = os.getenv("SHAREPOINT_SITE_NAME")
SITE_PATH = os.getenv("SHAREPOINT_SITE_PATH")
DOMAIN = os.getenv("SHAREPOINT_DOMAIN", "elixirrkc.sharepoint.com")
SHAREPOINT_FOLDER_PATH = os.getenv("SHAREPOINT_FOLDER_PATH", "Shared Documents/기록")
BLOB_CONNECTION_STRING = os.getenv("BLOB_CONNECTION_STRING")
BLOB_CONTAINER_NAME = os.getenv("BLOB_CONTAINER_NAME", "meeting-videos")
BLOB_PREFIX = os.getenv("BLOB_PREFIX", "sharepoint-records")
DEBUG_TOKEN = os.getenv("DEBUG_TOKEN", "1") == "1"

# app | delegated
GRAPH_AUTH_MODE = os.getenv("GRAPH_AUTH_MODE", "app").strip().lower()
AUTHORITY_TENANT = os.getenv("AUTHORITY_TENANT", "organizations").strip()
DELEGATED_SCOPES_RAW = os.getenv(
    "DELEGATED_SCOPES",
    "https://graph.microsoft.com/Files.Read https://graph.microsoft.com/Sites.Read.All",
)

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


def parse_scopes(raw: str) -> list[str]:
    reserved = {"openid", "offline_access", "profile"}
    chunks = raw.replace(",", " ").split()
    scopes = [c.strip() for c in chunks if c.strip()]
    cleaned = [s for s in scopes if s.lower() not in reserved]
    removed = [s for s in scopes if s.lower() in reserved]
    if removed:
        print(f"Removed reserved scopes for device flow: {removed}")
    if not cleaned:
        raise RuntimeError("No usable delegated scopes left after removing reserved values.")
    return cleaned


def validate_config() -> None:
    if GRAPH_AUTH_MODE not in {"app", "delegated"}:
        raise RuntimeError("GRAPH_AUTH_MODE must be either 'app' or 'delegated'.")

    base_required = ["CLIENT_ID", "SHAREPOINT_SITE_NAME", "BLOB_CONNECTION_STRING"]
    missing = [k for k in base_required if not os.getenv(k)]

    if GRAPH_AUTH_MODE == "app":
        app_required = ["TENANT_ID", "CLIENT_SECRET"]
        missing.extend([k for k in app_required if not os.getenv(k)])

    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(sorted(set(missing)))}")


def get_access_token() -> str:
    if GRAPH_AUTH_MODE == "delegated":
        return get_access_token_delegated()
    return get_access_token_app()


def get_access_token_app() -> str:
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    response = requests.post(url, data=data, timeout=30)
    response.raise_for_status()
    return response.json()["access_token"]


def get_access_token_delegated() -> str:
    try:
        import msal
    except Exception as exc:
        raise RuntimeError("Delegated mode requires 'msal'. Install with: pip install msal") from exc

    scopes = parse_scopes(DELEGATED_SCOPES_RAW)
    authority = f"https://login.microsoftonline.com/{AUTHORITY_TENANT}"

    app = msal.PublicClientApplication(client_id=CLIENT_ID, authority=authority)

    result = None
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(scopes=scopes, account=accounts[0])

    if not result:
        flow = app.initiate_device_flow(scopes=scopes)
        if "user_code" not in flow:
            raise RuntimeError(f"Failed to initiate device flow: {flow}")

        print("Delegated sign-in required. Complete login in browser:")
        print(flow.get("message", ""))
        result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise RuntimeError(
            "Failed to get delegated token. "
            f"error={result.get('error')}, description={result.get('error_description')}"
        )

    return result["access_token"]


def _decode_jwt_payload(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return {}
        payload_b64 = parts[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
        return json.loads(payload_json)
    except Exception:
        return {}


def print_token_debug(token: str) -> None:
    payload = _decode_jwt_payload(token)
    print("Token debug:")
    print(f"  auth_mode: {GRAPH_AUTH_MODE}")
    print(f"  aud: {payload.get('aud')}")
    print(f"  tid: {payload.get('tid')}")
    print(f"  appid: {payload.get('appid')}")
    print(f"  upn: {payload.get('upn')}")
    print(f"  roles: {payload.get('roles', [])}")
    print(f"  scp: {payload.get('scp')}")


def normalize_site_inputs() -> tuple[str, str]:
    raw_name = (SITE_NAME or "").strip()
    raw_path = (SITE_PATH or "").strip()

    if raw_name.startswith("/sites/") or raw_name.startswith("/teams/"):
        raw_path = raw_name
        raw_name = raw_name.rstrip("/").split("/")[-1]

    if raw_path and not raw_path.startswith("/"):
        raw_path = f"/{raw_path}"

    return raw_name, raw_path


def graph_get(url: str, token: str) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers, timeout=60)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(
            f"Graph request failed: {response.status_code} {url}\n{response.text}"
        ) from exc
    return response.json()


def try_graph_get(url: str, token: str, errors: list[str]) -> dict | None:
    try:
        return graph_get(url, token)
    except Exception as exc:
        errors.append(f"{url} -> {exc}")
        return None


def get_site_id(token: str) -> str:
    site_name, site_path = normalize_site_inputs()

    candidate_paths = []
    if site_path:
        candidate_paths.append(site_path)

    candidate_paths.extend([f"/sites/{site_name}", f"/teams/{site_name}"])

    errors: list[str] = []

    for path in candidate_paths:
        encoded_path = quote(path, safe="/-_.")
        candidate_urls = [
            f"{GRAPH_BASE_URL}/sites/{DOMAIN}:{encoded_path}",
            f"{GRAPH_BASE_URL}/sites/{DOMAIN}:{encoded_path}:",
        ]
        for url in candidate_urls:
            payload = try_graph_get(url, token, errors)
            if payload and payload.get("id"):
                return payload["id"]

    search_url = f"{GRAPH_BASE_URL}/sites?search={quote(site_name)}"
    search_payload = try_graph_get(search_url, token, errors)
    if search_payload:
        for site in search_payload.get("value", []):
            web_url = site.get("webUrl", "")
            if f"/{site_name}" in web_url:
                return site["id"]

    error_tail = " | ".join(errors[-4:])
    raise RuntimeError(
        "Unable to resolve SharePoint site ID. "
        f"SITE_NAME={site_name}, SITE_PATH={site_path}, DOMAIN={DOMAIN}. "
        f"Last errors: {error_tail}"
    )


def iter_files_in_folder(token: str, site_id: str, folder_path: str) -> Iterable[dict]:
    encoded_path = quote(folder_path, safe="/-_.() ")
    next_url = f"{GRAPH_BASE_URL}/sites/{site_id}/drive/root:/{encoded_path}:/children"

    while next_url:
        payload = graph_get(next_url, token)

        for item in payload.get("value", []):
            if "file" in item:
                yield item
            elif "folder" in item:
                parent_path = item["parentReference"]["path"].split("root:", 1)[-1].strip("/")
                child_path = f"{parent_path}/{item['name']}".strip("/")
                yield from iter_files_in_folder(token, site_id, child_path)

        next_url = payload.get("@odata.nextLink")


def upload_file_to_blob(container_client, item: dict) -> str:
    download_url = item.get("@microsoft.graph.downloadUrl")
    if not download_url:
        raise RuntimeError(f"Download URL not found for file: {item.get('name')}")

    parent_path = item.get("parentReference", {}).get("path", "").split("root:", 1)[-1].strip("/")
    if parent_path:
        blob_name = f"{BLOB_PREFIX}/{parent_path}/{item['name']}"
    else:
        blob_name = f"{BLOB_PREFIX}/{item['name']}"

    file_response = requests.get(download_url, timeout=120)
    file_response.raise_for_status()

    container_client.upload_blob(name=blob_name, data=file_response.content, overwrite=True)
    return blob_name


def main() -> None:
    validate_config()

    token = get_access_token()
    print("Access token acquired")
    if DEBUG_TOKEN:
        print_token_debug(token)

    site_id = get_site_id(token)
    print(f"Site ID: {site_id}")

    blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(BLOB_CONTAINER_NAME)

    try:
        container_client.create_container()
        print(f"Created blob container: {BLOB_CONTAINER_NAME}")
    except Exception:
        print(f"Using existing blob container: {BLOB_CONTAINER_NAME}")

    print(f"Scanning SharePoint folder: {SHAREPOINT_FOLDER_PATH}")
    uploaded = 0
    for item in iter_files_in_folder(token, site_id, SHAREPOINT_FOLDER_PATH):
        blob_name = upload_file_to_blob(container_client, item)
        uploaded += 1
        print(f"Uploaded: {blob_name}")

    print(f"Done. Uploaded {uploaded} file(s)")


if __name__ == "__main__":
    main()
