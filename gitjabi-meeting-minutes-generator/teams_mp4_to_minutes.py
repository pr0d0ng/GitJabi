import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

from graph_api import (
    SHAREPOINT_FOLDER_PATH,
    get_access_token,
    get_site_id,
    iter_files_in_folder,
)


PROJECT_ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download one MP4 from Teams/SharePoint, generate minutes, and upload to Blob."
    )
    parser.add_argument("--folder-path", type=str, default=SHAREPOINT_FOLDER_PATH)
    parser.add_argument("--download-dir", type=str, default="temp/teams_videos")
    parser.add_argument("--minutes-output-dir", type=str, default="out/meeting_minutes")
    parser.add_argument("--blob-prefix", type=str, default="meeting-minutes")
    parser.add_argument("--pick", choices=["latest"], default="latest")
    parser.add_argument("--name-contains", type=str, default="")
    parser.add_argument("--output-stem", type=str, default="")
    parser.add_argument("--skip-stt", action="store_true")
    parser.add_argument("--no-blob-upload", action="store_true")
    parser.add_argument("--key-limit", type=int, default=180)
    parser.add_argument("--action-limit", type=int, default=120)
    parser.add_argument("--other-sample-limit", type=int, default=20)
    parser.add_argument("--max-prompt-chars", type=int, default=18000)
    parser.add_argument("--meeting-datetime", type=str, default="")
    return parser.parse_args()


def parse_graph_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    # Graph examples: 2026-02-13T09:10:31Z
    if value.endswith("Z"):
        value = value.replace("Z", "+00:00")
    return datetime.fromisoformat(value)


def select_mp4_file(files: list[dict], name_contains: str) -> dict:
    mp4s = []
    for item in files:
        name = str(item.get("name", ""))
        if not name.lower().endswith(".mp4"):
            continue
        if name_contains and name_contains.lower() not in name.lower():
            continue
        mp4s.append(item)

    if not mp4s:
        raise RuntimeError("No matching .mp4 file found in SharePoint folder.")

    mp4s.sort(
        key=lambda x: parse_graph_dt(x.get("lastModifiedDateTime") or x.get("createdDateTime")),
        reverse=True,
    )
    return mp4s[0]


def download_graph_file(item: dict, download_dir: Path) -> tuple[Path, str]:
    download_url = item.get("@microsoft.graph.downloadUrl")
    if not download_url:
        raise RuntimeError("Selected file does not include @microsoft.graph.downloadUrl")

    dt = parse_graph_dt(item.get("lastModifiedDateTime") or item.get("createdDateTime"))
    stem = dt.astimezone(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"{stem}.mp4"

    download_dir.mkdir(parents=True, exist_ok=True)
    local_path = download_dir / filename

    with requests.get(download_url, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    return local_path, stem


def run_minutes_pipeline(local_media_path: Path, output_stem: str, args: argparse.Namespace) -> None:
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "meeting_minutes_pipeline.py"),
        "--media",
        str(local_media_path),
        "--output-stem",
        output_stem,
        "--minutes-output-dir",
        str(Path(args.minutes_output_dir).resolve()),
        "--blob-prefix",
        args.blob_prefix,
        "--key-limit",
        str(args.key_limit),
        "--action-limit",
        str(args.action_limit),
        "--other-sample-limit",
        str(args.other_sample_limit),
        "--max-prompt-chars",
        str(args.max_prompt_chars),
        "--meeting-datetime",
        str(args.meeting_datetime or ""),
    ]
    if args.skip_stt:
        cmd.append("--skip-stt")
    if args.no_blob_upload:
        cmd.append("--no-blob-upload")

    print("Running minutes pipeline...")
    subprocess.run(cmd, check=True)


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    args = parse_args()

    print("Resolving SharePoint site...")
    token = get_access_token()
    site_id = get_site_id(token)
    print(f"Site ID: {site_id}")

    print(f"Listing files in folder: {args.folder_path}")
    files = list(iter_files_in_folder(token, site_id, args.folder_path))
    selected = select_mp4_file(files, args.name_contains)
    print(
        "Selected MP4:",
        selected.get("name"),
        selected.get("lastModifiedDateTime") or selected.get("createdDateTime"),
    )

    last_modified = selected.get("lastModifiedDateTime") or selected.get("createdDateTime") or ""
    local_path, detected_output_stem = download_graph_file(selected, Path(args.download_dir).resolve())
    output_stem = args.output_stem.strip() or detected_output_stem
    print(f"Downloaded: {local_path}")
    print(f"Output stem (saved datetime): {output_stem}")

    # Pass source file datetime so minutes can use it as meeting datetime fallback.
    args.meeting_datetime = str(last_modified)
    run_minutes_pipeline(local_path, output_stem, args)
    print("Done.")


if __name__ == "__main__":
    main()
