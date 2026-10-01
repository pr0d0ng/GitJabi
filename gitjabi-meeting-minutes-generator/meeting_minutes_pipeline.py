import argparse
from datetime import datetime
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent


def get_env(key: str, default: str | None = None) -> str | None:
    value = os.getenv(key)
    if value:
        return value
    value = os.getenv(f'"{key}"')
    if value:
        return value
    value = os.getenv(f"\ufeff{key}")
    if value:
        return value
    return default


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run STT+key/action -> Llama minutes generation -> upload outputs to Blob."
    )
    parser.add_argument("--media", type=str, default="meeting_test.mp4")
    parser.add_argument("--output-stem", type=str, default=None)
    parser.add_argument("--stt-output-dir", type=str, default="whisperx-worker/out")
    parser.add_argument("--minutes-output-dir", type=str, default="out/meeting_minutes")
    parser.add_argument("--blob-prefix", type=str, default="meeting-minutes")
    parser.add_argument("--event-user-id", type=str, default=os.getenv("GRAPH_EVENT_USER_ID"))
    parser.add_argument("--event-id", type=str, default=os.getenv("GRAPH_EVENT_ID"))
    parser.add_argument("--meeting-datetime", type=str, default="")
    parser.add_argument("--no-blob-upload", action="store_true")
    parser.add_argument("--skip-stt", action="store_true")
    parser.add_argument("--stt-chunk-minutes", type=int, default=0)

    # Prompt controls for long meetings
    parser.add_argument("--key-limit", type=int, default=180)
    parser.add_argument("--action-limit", type=int, default=120)
    parser.add_argument("--other-sample-limit", type=int, default=20)
    parser.add_argument("--max-prompt-chars", type=int, default=18000)
    parser.add_argument("--min-key-retain", type=int, default=40)
    parser.add_argument("--min-action-retain", type=int, default=20)

    return parser.parse_args()


def require_env_vars(*keys: str) -> None:
    missing = [k for k in keys if not get_env(k)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


def run_whisperx_pipeline(media_path: Path, output_dir: Path) -> Path:
    cmd = [
        sys.executable,
        str(Path("whisperx-worker") / "whisperx_key_action_pipeline.py"),
        "--audio",
        str(media_path),
        "--output-dir",
        str(output_dir),
    ]
    print("Running WhisperX pipeline...")
    subprocess.run(cmd, check=True)
    result_json = output_dir / f"{media_path.stem}.key_action.json"
    if not result_json.exists():
        raise FileNotFoundError(f"Expected WhisperX result not found: {result_json}")
    return result_json


def probe_media_duration_sec(media_path: Path) -> float | None:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(media_path),
    ]
    try:
        p = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return float((p.stdout or "").strip())
    except Exception:
        return None


def split_media_into_chunks(media_path: Path, chunk_sec: int, chunk_dir: Path) -> list[Path]:
    chunk_dir.mkdir(parents=True, exist_ok=True)
    out_pattern = str(chunk_dir / f"{media_path.stem}.part_%03d{media_path.suffix}")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(media_path),
        "-f",
        "segment",
        "-segment_time",
        str(chunk_sec),
        "-c",
        "copy",
        out_pattern,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    chunks = sorted(chunk_dir.glob(f"{media_path.stem}.part_*{media_path.suffix}"))
    if not chunks:
        raise RuntimeError("Chunk split produced no files.")
    return chunks


def merge_chunk_key_action_payloads(
    chunk_payloads: list[dict[str, Any]],
    chunk_durations: list[float],
    original_media_path: Path,
) -> dict[str, Any]:
    if not chunk_payloads:
        raise RuntimeError("No chunk payloads to merge.")

    merged = dict(chunk_payloads[0])
    merged["audio_file"] = str(original_media_path)
    merged_utterances: list[dict[str, Any]] = []
    offset = 0.0
    next_utt_id = 1
    total_elapsed = 0.0

    for payload, dur in zip(chunk_payloads, chunk_durations):
        total_elapsed += float(payload.get("elapsed_sec", 0.0) or 0.0)
        for u in payload.get("utterances", []):
            m = dict(u)
            m["utt_id"] = next_utt_id
            next_utt_id += 1
            m["start"] = round(float(m.get("start", 0.0)) + offset, 3)
            m["end"] = round(float(m.get("end", 0.0)) + offset, 3)
            merged_utterances.append(m)
        offset += float(dur)

    counts = {"action": 0, "key": 0, "other": 0}
    for u in merged_utterances:
        c = str(u.get("line_class", "other"))
        counts[c] = counts.get(c, 0) + 1

    merged["utterances"] = merged_utterances
    merged["n_utterances"] = len(merged_utterances)
    merged["counts"] = counts
    merged["elapsed_sec"] = round(total_elapsed, 2)
    merged["suspicious_spans"] = []
    return merged


def run_whisperx_pipeline_chunked(media_path: Path, output_dir: Path, chunk_minutes: int) -> Path:
    if chunk_minutes <= 0:
        return run_whisperx_pipeline(media_path, output_dir)

    duration = probe_media_duration_sec(media_path)
    chunk_sec = max(60, int(chunk_minutes * 60))
    if duration and duration <= chunk_sec:
        return run_whisperx_pipeline(media_path, output_dir)

    chunk_dir = output_dir / "_chunks" / media_path.stem
    chunks = split_media_into_chunks(media_path, chunk_sec, chunk_dir)
    print(f"Chunk STT enabled: {len(chunks)} chunks, {chunk_minutes} min each")

    chunk_payloads: list[dict[str, Any]] = []
    chunk_durations: list[float] = []
    for i, chunk_path in enumerate(chunks):
        print(f"Running WhisperX on chunk {i + 1}/{len(chunks)}: {chunk_path.name}")
        chunk_json = run_whisperx_pipeline(chunk_path, output_dir)
        chunk_payloads.append(load_key_action_payload(chunk_json))
        chunk_durations.append(probe_media_duration_sec(chunk_path) or float(chunk_sec))

    merged_payload = merge_chunk_key_action_payloads(chunk_payloads, chunk_durations, media_path)
    merged_json = output_dir / f"{media_path.stem}.key_action.json"
    with open(merged_json, "w", encoding="utf-8") as f:
        json.dump(merged_payload, f, ensure_ascii=False, indent=2)
    return merged_json


def load_key_action_payload(result_json: Path) -> dict[str, Any]:
    with open(result_json, "r", encoding="utf-8") as f:
        return json.load(f)


def try_get_graph_event_info(event_user_id: str | None, event_id: str | None) -> dict[str, Any]:
    if not event_user_id or not event_id:
        return {}
    try:
        from graph_api import get_access_token, graph_get
    except Exception as exc:
        print(f"Graph import skipped: {exc}")
        return {}

    try:
        token = get_access_token()
        url = (
            "https://graph.microsoft.com/v1.0/"
            f"users/{event_user_id}/events/{event_id}"
            "?$select=subject,start,end,attendees,onlineMeetingProvider,isOnlineMeeting"
        )
        event = graph_get(url, token)
    except Exception as exc:
        print(f"Graph event lookup failed: {exc}")
        return {}

    attendees = []
    for a in event.get("attendees", []):
        email = a.get("emailAddress", {})
        name = email.get("name") or email.get("address")
        if name:
            attendees.append(name)

    return {
        "meeting_name": event.get("subject"),
        "start": (event.get("start") or {}).get("dateTime"),
        "end": (event.get("end") or {}).get("dateTime"),
        "is_online": bool(event.get("isOnlineMeeting")),
        "online_provider": event.get("onlineMeetingProvider"),
        "attendees": attendees,
    }


def sample_other_lines(other_lines: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if limit <= 0 or not other_lines:
        return []
    if len(other_lines) <= limit:
        return other_lines

    picks = []
    n = len(other_lines)
    for i in range(limit):
        idx = int(round(i * (n - 1) / max(limit - 1, 1)))
        picks.append(other_lines[idx])
    return picks


def format_lines(lines: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"- [{u.get('speaker')}] ({float(u.get('start', 0.0)):.1f}-{float(u.get('end', 0.0)):.1f}s) {u.get('text')}"
        for u in lines
    )


def extract_action_candidates(action_lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    due_patterns = [
        r"\d{1,2}월\s*\d{1,2}일(?:까지|부터)?",
        r"\d{1,2}일(?:까지|부터)?",
        r"내일(?:까지|부터)?",
        r"오늘(?:까지|부터)?",
        r"이번주(?:까지|부터)?",
        r"다음주(?:까지|부터)?",
        r"수요일(?:까지|부터)?",
        r"목요일(?:까지|부터)?",
        r"금요일(?:까지|부터)?",
        r"토요일(?:까지|부터)?",
        r"일요일(?:까지|부터)?",
    ]
    assignee_patterns = [
        r"([가-힣]{2,4})님",
        r"(SPEAKER_\d+)",
    ]
    task_hint_patterns = [
        r"(PPT[^,.!?]{0,80})",
        r"(템플릿[^,.!?]{0,80})",
        r"(발표[^,.!?]{0,80})",
        r"(백엔드[^,.!?]{0,80})",
        r"(프론트엔드[^,.!?]{0,80})",
        r"(데이터베이스[^,.!?]{0,80})",
        r"(정리[^,.!?]{0,80})",
        r"(작업[^,.!?]{0,80})",
    ]

    candidates: list[dict[str, Any]] = []
    for u in action_lines:
        text = str(u.get("text", "")).strip()
        if not text:
            continue

        due_matches = []
        for p in due_patterns:
            for m in re.finditer(p, text):
                due_matches.append((m.group(0), m.start(), m.end()))

        assignee = None
        for p in assignee_patterns:
            m = re.search(p, text)
            if m:
                assignee = m.group(1)
                break
        if not assignee:
            assignee = str(u.get("speaker", "UNKNOWN"))

        task = None
        task_span = None
        for p in task_hint_patterns:
            m = re.search(p, text)
            if m:
                task = m.group(1).strip()
                task_span = (m.start(), m.end())
                break
        if not task:
            task = text[:120]

        # Pick date closest to task span; this avoids choosing prerequisite dates like
        # "24일까지 ... 되면 수요일부터 PPT 작업" where task schedule is "수요일부터".
        due = None
        if due_matches:
            if task_span:
                ts, te = task_span
                due_matches.sort(key=lambda x: min(abs(x[1] - te), abs(x[2] - ts)))
                due = due_matches[0][0]
            else:
                due = due_matches[0][0]

        if due or re.search(r"(하자|해야|진행|작업|정리|준비|등록|반영|제출|완료)", text):
            candidates.append(
                {
                    "assignee": assignee,
                    "task": task,
                    "due": due or "미확인",
                    "source_text": text,
                    "speaker": u.get("speaker"),
                    "start": float(u.get("start", 0.0)),
                    "end": float(u.get("end", 0.0)),
                }
            )

    candidates.sort(key=lambda x: (x["due"] == "미확인", x["start"]))
    return candidates[:30]


def format_action_candidates(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return "- (없음)"
    return "\n".join(
        f"- 담당: {c['assignee']} / 기한: {c['due']} / 작업: {c['task']} / 근거: {c['source_text']}"
        for c in candidates
    )


def render_minutes_prompt(
    media_name: str,
    meeting_name: str,
    start: str,
    end: str,
    meeting_mode: str,
    attendees: list[str],
    speakers: list[str],
    key_lines: list[dict[str, Any]],
    action_lines: list[dict[str, Any]],
    action_candidates: list[dict[str, Any]],
    other_sample: list[dict[str, Any]],
) -> str:
    return f"""
당신은 한국어 회의록 전문 비서입니다.
아래 데이터만 근거로 회의록을 작성하세요. 데이터에 없는 사실은 쓰지 마세요.
한자(漢字)나 깨진 문자로 쓰지 말고 자연스러운 한국어만 사용하세요.

출력 규칙:
- 아래 1~6 섹션 제목과 순서를 반드시 유지
- 정보가 없으면 '미확인'이라고 명시
- Decision은 합의/확정 표현이 근거일 때만 작성
- Action Item은 절대 발화 원문 복붙하지 말고 `담당 / 기한 / 작업` 형태로 정리
- [구조화 Action 후보]는 보조 힌트이며, 원문 발화와 충돌하면 원문을 우선

출력 형식:
1. 회의 기본 정보
회의명:
일시:
방식:

2. 참석자

3. 회의 목적

4. 안건별 논의 내용

5. 결정 사항 (Decision)

6. Action Item

[메타데이터]
- 파일명: {media_name}
- 회의명 후보: {meeting_name}
- 시작시각 후보: {start}
- 종료시각 후보: {end}
- 방식 후보: {meeting_mode}
- 참석자 후보: {', '.join(attendees)}
- 화자 라벨: {', '.join(speakers)}

[핵심 발화(key)]
{format_lines(key_lines) if key_lines else '- (없음)'}

[액션 발화(action)]
{format_lines(action_lines) if action_lines else '- (없음)'}

[구조화 Action 후보(규칙 추출)]
{format_action_candidates(action_candidates)}

[맥락 발화(other 샘플)]
{format_lines(other_sample) if other_sample else '- (없음)'}
""".strip()


def build_llama_prompt(
    media_name: str,
    key_action_payload: dict[str, Any],
    graph_info: dict[str, Any],
    args: argparse.Namespace,
) -> str:
    utterances = key_action_payload.get("utterances", [])
    key_lines = [u for u in utterances if u.get("line_class") == "key"][: args.key_limit]
    action_lines = [u for u in utterances if u.get("line_class") == "action"][: args.action_limit]
    other_lines = [u for u in utterances if u.get("line_class") == "other"]
    other_sample = sample_other_lines(other_lines, args.other_sample_limit)
    action_candidates = extract_action_candidates(action_lines)

    speakers = sorted({str(u.get("speaker", "UNKNOWN")) for u in utterances})

    meeting_name = graph_info.get("meeting_name") or media_name
    start = graph_info.get("start") or "미확인"
    end = graph_info.get("end") or "미확인"
    attendees = graph_info.get("attendees") or speakers
    meeting_mode = "Microsoft Teams 비대면 회의" if graph_info.get("is_online") else "미확인"

    prompt = render_minutes_prompt(
        media_name=media_name,
        meeting_name=meeting_name,
        start=start,
        end=end,
        meeting_mode=meeting_mode,
        attendees=attendees,
        speakers=speakers,
        key_lines=key_lines,
        action_lines=action_lines,
        action_candidates=action_candidates,
        other_sample=other_sample,
    )

    if len(prompt) > args.max_prompt_chars:
        while len(prompt) > args.max_prompt_chars and other_sample:
            other_sample = other_sample[:-1]
            prompt = render_minutes_prompt(
                media_name=media_name,
                meeting_name=meeting_name,
                start=start,
                end=end,
                meeting_mode=meeting_mode,
                attendees=attendees,
                speakers=speakers,
                key_lines=key_lines,
                action_lines=action_lines,
                action_candidates=action_candidates,
                other_sample=other_sample,
            )

        while len(prompt) > args.max_prompt_chars and len(action_candidates) > max(args.min_action_retain, 0):
            action_candidates = action_candidates[:-1]
            prompt = render_minutes_prompt(
                media_name=media_name,
                meeting_name=meeting_name,
                start=start,
                end=end,
                meeting_mode=meeting_mode,
                attendees=attendees,
                speakers=speakers,
                key_lines=key_lines,
                action_lines=action_lines,
                action_candidates=action_candidates,
                other_sample=other_sample,
            )

        while len(prompt) > args.max_prompt_chars and len(action_lines) > max(args.min_action_retain, 0):
            action_lines = action_lines[:-1]
            prompt = render_minutes_prompt(
                media_name=media_name,
                meeting_name=meeting_name,
                start=start,
                end=end,
                meeting_mode=meeting_mode,
                attendees=attendees,
                speakers=speakers,
                key_lines=key_lines,
                action_lines=action_lines,
                action_candidates=action_candidates,
                other_sample=other_sample,
            )

        while len(prompt) > args.max_prompt_chars and len(key_lines) > max(args.min_key_retain, 0):
            key_lines = key_lines[:-1]
            prompt = render_minutes_prompt(
                media_name=media_name,
                meeting_name=meeting_name,
                start=start,
                end=end,
                meeting_mode=meeting_mode,
                attendees=attendees,
                speakers=speakers,
                key_lines=key_lines,
                action_lines=action_lines,
                action_candidates=action_candidates,
                other_sample=other_sample,
            )

    print(
        "Prompt stats:",
        f"key={len(key_lines)}",
        f"action={len(action_lines)}",
        f"other_sample={len(other_sample)}",
        f"action_candidates={len(action_candidates)}",
        f"min_key_retain={args.min_key_retain}",
        f"min_action_retain={args.min_action_retain}",
        f"chars={len(prompt)}",
    )
    return prompt


def call_databricks_llama(prompt: str) -> str:
    endpoint = get_env("LLAMA_ENDPOINT")
    token = get_env("DATABRICKS_TOKEN")
    if not endpoint or not token:
        raise RuntimeError(
            "Missing LLAMA_ENDPOINT or DATABRICKS_TOKEN "
            f"(cwd={Path.cwd()}, dotenv={PROJECT_ROOT / '.env'})"
        )

    payload = {
        "messages": [
            {"role": "system", "content": "당신은 회의록 작성 비서다. 사실 기반으로만 간결하게 작성한다."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 3500,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    resp = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    if isinstance(data, dict) and data.get("choices"):
        return data["choices"][0]["message"]["content"].strip()
    if isinstance(data, dict) and data.get("predictions"):
        return str(data["predictions"][0]).strip()
    if isinstance(data, dict) and data.get("output"):
        return str(data["output"]).strip()
    raise RuntimeError(f"Unexpected LLM response shape: {str(data)[:500]}")



def _format_kr_datetime(dt: datetime) -> str:
    return f"{dt.year}년 {dt.month}월 {dt.day}일 {dt.strftime('%H:%M')}"


def parse_datetime_hint(value: str | None) -> datetime | None:
    if not value:
        return None
    v = value.strip()
    if not v:
        return None
    if v.endswith("Z"):
        v = v.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(v)
    except Exception:
        return None


def patch_minutes_datetime(
    minutes_text: str,
    generated_at: datetime,
    meeting_datetime_hint: str | None,
) -> str:
    # If model left meeting time unknown, fill with source file datetime first,
    # and fallback to minutes generation time.
    hinted = parse_datetime_hint(meeting_datetime_hint)
    if hinted:
        replacement = f"일시: {_format_kr_datetime(hinted)} (원본 파일 수정시각)"
    else:
        replacement = f"일시: {_format_kr_datetime(generated_at)} (회의록 생성시각)"
    return re.sub(
        r"^일시:\s*(미확인|미상)\s*$",
        replacement,
        minutes_text,
        flags=re.MULTILINE,
    )
def save_outputs(
    output_dir: Path,
    stem: str,
    minutes_text: str,
    key_action_payload: dict[str, Any],
    graph_info: dict[str, Any],
    meeting_datetime_hint: str | None = None,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    minutes_path = output_dir / f"{stem}.minutes.md"
    meta_path = output_dir / f"{stem}.minutes.meta.json"
    generated_at = datetime.now()
    patched_minutes = patch_minutes_datetime(minutes_text, generated_at, meeting_datetime_hint)

    with open(minutes_path, "w", encoding="utf-8") as f:
        f.write(patched_minutes.strip() + "\n")

    meta = {
        "source_audio_or_video": key_action_payload.get("audio_file"),
        "n_utterances": key_action_payload.get("n_utterances"),
        "counts": key_action_payload.get("counts"),
        "graph_info": graph_info,
        "meeting_datetime_hint": meeting_datetime_hint,
        "minutes_generated_at": generated_at.isoformat(timespec="seconds"),
        "minutes_file": str(minutes_path),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return minutes_path, meta_path


def upload_to_blob(paths: list[Path], blob_prefix: str) -> None:
    require_env_vars("BLOB_CONNECTION_STRING")
    conn = get_env("BLOB_CONNECTION_STRING")
    container = get_env("BLOB_CONTAINER_NAME", "meeting-videos")
    service = BlobServiceClient.from_connection_string(conn)
    container_client = service.get_container_client(container)
    try:
        container_client.create_container()
    except Exception:
        pass

    for p in paths:
        blob_name = f"{blob_prefix}/{p.name}"
        with open(p, "rb") as f:
            container_client.upload_blob(name=blob_name, data=f, overwrite=True)
        print(f"Uploaded blob: {blob_name}")


def main() -> None:
    timings: dict[str, float] = {}
    t0 = time.perf_counter()
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    args = parse_args()
    media_path = Path(args.media).resolve()
    stt_output_dir = Path(args.stt_output_dir).resolve()
    minutes_output_dir = Path(args.minutes_output_dir).resolve()

    if not media_path.exists():
        raise FileNotFoundError(f"Media file not found: {media_path}")

    if args.skip_stt:
        s0 = time.perf_counter()
        result_json = stt_output_dir / f"{media_path.stem}.key_action.json"
        if not result_json.exists():
            raise FileNotFoundError(f"--skip-stt set but missing file: {result_json}")
        timings["stt_or_load"] = round(time.perf_counter() - s0, 3)
    else:
        s0 = time.perf_counter()
        result_json = run_whisperx_pipeline_chunked(
            media_path=media_path,
            output_dir=stt_output_dir,
            chunk_minutes=int(args.stt_chunk_minutes or 0),
        )
        timings["stt_or_load"] = round(time.perf_counter() - s0, 3)

    s0 = time.perf_counter()
    key_action_payload = load_key_action_payload(result_json)
    timings["load_key_action_payload"] = round(time.perf_counter() - s0, 3)
    s0 = time.perf_counter()
    graph_info = try_get_graph_event_info(args.event_user_id, args.event_id)
    timings["graph_event_lookup"] = round(time.perf_counter() - s0, 3)

    s0 = time.perf_counter()
    prompt = build_llama_prompt(media_path.name, key_action_payload, graph_info, args)
    timings["build_prompt"] = round(time.perf_counter() - s0, 3)
    print("Calling Databricks Llama for meeting minutes...")
    s0 = time.perf_counter()
    minutes_text = call_databricks_llama(prompt)
    timings["llama_call"] = round(time.perf_counter() - s0, 3)

    output_stem = args.output_stem or media_path.stem
    s0 = time.perf_counter()
    minutes_path, meta_path = save_outputs(
        output_dir=minutes_output_dir,
        stem=output_stem,
        minutes_text=minutes_text,
        key_action_payload=key_action_payload,
        graph_info=graph_info,
        meeting_datetime_hint=args.meeting_datetime,
    )
    timings["save_outputs"] = round(time.perf_counter() - s0, 3)
    print(f"Saved minutes: {minutes_path}")
    print(f"Saved metadata: {meta_path}")

    if not args.no_blob_upload:
        s0 = time.perf_counter()
        upload_to_blob([minutes_path, meta_path], args.blob_prefix)
        timings["upload_blob"] = round(time.perf_counter() - s0, 3)
    else:
        print("Skipped Blob upload (--no-blob-upload).")
        timings["upload_blob"] = 0.0

    timings["total"] = round(time.perf_counter() - t0, 3)
    print("Timing (sec):", json.dumps(timings, ensure_ascii=False))

    # Persist timings to metadata for operational diagnostics.
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["timings_sec"] = timings
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


if __name__ == "__main__":
    main()



