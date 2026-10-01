import os
import json
import glob
import time
import sys
import re
import urllib.request
import urllib.error

ROOT = os.path.abspath(os.getcwd())


def _load_dotenv(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().strip('"').strip("'")
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


DATASETS_GLOB = os.path.join(ROOT, "datasets", "*", "dialogueActs", "*.json")
_load_dotenv(os.path.join(ROOT, ".env"))
ENDPOINT = os.getenv("LLAMA_ENDPOINT")
TOKEN = os.getenv("DATABRICKS_TOKEN")

if not ENDPOINT or not TOKEN:
    print("Missing LLAMA_ENDPOINT or DATABRICKS_TOKEN in environment.")
    sys.exit(1)

SYSTEM_PROMPT = (
    "You are a professional translator. Translate the given English utterances into natural Korean. "
    "Preserve any tags in angle brackets like <vocalsound> or <disfmarker> exactly as-is. "
    "Preserve speaker names, IDs, and punctuation. Do NOT add explanations. "
    "Return the translations joined by the delimiter |||SEP||| in order. Do not add extra text. "
    "Use natural spoken Korean for a meeting context (colloquial but polite). Avoid stiff written style. "
    "Output only Korean (Hangul) and required symbols; do NOT use Chinese characters."
)


def _post_json(url, payload, timeout=60):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw)


def _protect_tags(text):
    tags = re.findall(r"<[^>]+>", text)
    mapping = {}
    protected = text
    for i, tag in enumerate(tags):
        token = f"__TAG{i}__"
        mapping[token] = tag
        protected = protected.replace(tag, token)
    return protected, mapping


def _restore_tags(text, mapping):
    restored = text
    for token, tag in mapping.items():
        restored = restored.replace(token, tag)
    return restored


def _contains_cjk(text):
    for ch in text:
        code = ord(ch)
        if 0x4E00 <= code <= 0x9FFF:
            return True
    return False


def call_model(texts, max_retries=5):
    base_prompt = (
        "Translate each item to Korean in natural spoken meeting Korean (colloquial but polite). "
        "Avoid stiff written style. Preserve hesitations like 'um', 'uh' naturally "
        "(e.g., um -> 'eum', uh -> 'eo'). "
        "Do NOT translate tokens like __TAG0__. Keep them exactly as-is. "
        "Return the translations joined by the delimiter |||SEP||| in order, with no extra text. "
        "Output only Korean (Hangul) and required symbols; do NOT use Chinese characters.\n"
        "Items:\n" + "\n".join(texts)
    )
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": base_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 4096,
    }
    last_err = None
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                payload["messages"][1]["content"] = (
                    base_prompt
                    + "\nIMPORTANT: Use '|||SEP|||' between every translation, "
                    + "e.g., first|||SEP|||second."
                )
            else:
                payload["messages"][1]["content"] = base_prompt

            data = _post_json(ENDPOINT, payload, timeout=60)
            content = None
            if isinstance(data, dict):
                if "choices" in data and data["choices"]:
                    content = data["choices"][0].get("message", {}).get("content")
                elif "predictions" in data and data["predictions"]:
                    content = data["predictions"][0]
                elif "output" in data:
                    content = data["output"]
            if content is None:
                last_err = f"Unexpected response shape: {str(data)[:500]}"
                time.sleep(2 + attempt)
                continue
            content_str = content.strip()
            translated = [part.strip() for part in content_str.split("|||SEP|||")]
            if len(translated) != len(texts):
                last_err = f"Length mismatch. got {len(translated)} expected {len(texts)}"
                time.sleep(2 + attempt)
                continue
            if any(_contains_cjk(t) for t in translated):
                last_err = "CJK characters detected in output."
                time.sleep(2 + attempt)
                continue
            return translated
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            last_err = f"HTTP {e.code}: {body[:500]}"
            if e.code in (413, 414, 422):
                raise ValueError("payload_too_large")
            if e.code == 429:
                time.sleep(10 + attempt * 2)
                continue
            time.sleep(2 + attempt)
        except ValueError as ve:
            if str(ve) == "payload_too_large":
                raise
            last_err = str(ve)
            time.sleep(2 + attempt)
        except Exception as e:
            last_err = str(e)
            time.sleep(2 + attempt)
    raise RuntimeError(last_err or "Unknown error")


def call_model_json(texts, max_retries=3):
    json_system = (
        "You are a professional translator. Translate the given English utterances into natural Korean. "
        "Preserve any tags in angle brackets like <vocalsound> or <disfmarker> exactly as-is. "
        "Preserve speaker names, IDs, and punctuation. Do NOT add explanations. "
        "Output only Korean (Hangul) and required symbols; do NOT use Chinese characters. "
        "Return ONLY a valid JSON array of strings, same length and order as the input, with no extra text."
    )
    base_prompt = (
        "Translate each item to Korean in natural spoken meeting Korean (colloquial but polite). "
        "Avoid stiff written style. Preserve hesitations like 'um', 'uh' naturally "
        "(e.g., um -> 'eum', uh -> 'eo'). "
        "Do NOT translate tokens like __TAG0__. Keep them exactly as-is. "
        "Input JSON:\n" + json.dumps(texts, ensure_ascii=False)
    )
    payload = {
        "messages": [
            {"role": "system", "content": json_system},
            {"role": "user", "content": base_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 4096,
    }
    last_err = None
    for attempt in range(max_retries):
        try:
            data = _post_json(ENDPOINT, payload, timeout=60)
            content = None
            if isinstance(data, dict):
                if "choices" in data and data["choices"]:
                    content = data["choices"][0].get("message", {}).get("content")
                elif "predictions" in data and data["predictions"]:
                    content = data["predictions"][0]
                elif "output" in data:
                    content = data["output"]
            if content is None:
                last_err = f"Unexpected response shape: {str(data)[:500]}"
                time.sleep(2 + attempt)
                continue
            content_str = content.strip()
            if not content_str.startswith("["):
                start = content_str.find("[")
                end = content_str.rfind("]")
                if start != -1 and end != -1 and end > start:
                    content_str = content_str[start : end + 1]
            translated = json.loads(content_str)
            if not isinstance(translated, list) or len(translated) != len(texts):
                last_err = f"Length mismatch. got {len(translated)} expected {len(texts)}"
                time.sleep(2 + attempt)
                continue
            if any(_contains_cjk(t) for t in translated):
                last_err = "CJK characters detected in output."
                time.sleep(2 + attempt)
                continue
            return translated
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")
            last_err = f"HTTP {e.code}: {body[:500]}"
            if e.code in (413, 414, 422):
                raise ValueError("payload_too_large")
            if e.code == 429:
                time.sleep(10 + attempt * 2)
                continue
            time.sleep(2 + attempt)
        except Exception as e:
            last_err = str(e)
            time.sleep(2 + attempt)
    raise RuntimeError(last_err or "Unknown error")


def _load_partial(partial_path, total_len):
    if not os.path.exists(partial_path):
        return None
    with open(partial_path, "r", encoding="utf-8") as f:
        state = json.load(f)
    translated_texts = state.get("translated_texts")
    idx = state.get("idx", 0)
    if not isinstance(translated_texts, list) or len(translated_texts) != total_len:
        return None
    if not isinstance(idx, int) or idx < 0 or idx > total_len:
        return None
    return {"translated_texts": translated_texts, "idx": idx}


def _save_partial(partial_path, translated_texts, idx):
    tmp_path = partial_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump({"translated_texts": translated_texts, "idx": idx}, f, ensure_ascii=False)
    os.replace(tmp_path, partial_path)


def translate_file(src_path, dst_path, chunk_size=120, max_chunks=None, max_seconds=None):
    with open(src_path, "r", encoding="utf-8") as f:
        items = json.load(f)
    texts = [item.get("text", "") for item in items]
    partial_path = dst_path + ".partial.json"
    state = _load_partial(partial_path, len(texts))
    if state:
        translated_texts = state["translated_texts"]
        idx = state["idx"]
        print(f"  resume from {idx}/{len(texts)}")
    else:
        translated_texts = [""] * len(texts)
        idx = 0

    current_chunk = chunk_size
    chunk_count = 0
    start_time = time.time()
    while idx < len(texts):
        if max_chunks is not None and chunk_count >= max_chunks:
            _save_partial(partial_path, translated_texts, idx)
            print(f"  reached MAX_CHUNKS={max_chunks}, saved partial.")
            return False
        if max_seconds is not None and (time.time() - start_time) >= max_seconds:
            _save_partial(partial_path, translated_texts, idx)
            print(f"  reached MAX_SECONDS={max_seconds}, saved partial.")
            return False
        chunk = texts[idx : idx + current_chunk]
        protected = []
        maps = []
        for t in chunk:
            pt, mp = _protect_tags(t)
            protected.append(pt)
            maps.append(mp)
        try:
            try:
                translated = call_model(protected)
            except RuntimeError:
                # Fallback to JSON mode when separator parsing is unstable
                translated = call_model_json(protected)
            restored = [_restore_tags(tr, mp) for tr, mp in zip(translated, maps)]
            translated_texts[idx : idx + current_chunk] = restored
            idx += current_chunk
            chunk_count += 1
            _save_partial(partial_path, translated_texts, idx)
            current_chunk = chunk_size
            print(f"  translated {idx}/{len(texts)}")
        except RuntimeError as e:
            if current_chunk > 20:
                current_chunk = max(20, current_chunk // 2)
                print(f"  retry with smaller chunk: {current_chunk} (error: {e})")
                time.sleep(2)
                continue
            raise
        except ValueError:
            if current_chunk > 20:
                current_chunk = max(20, current_chunk // 2)
                print(f"  payload too large, reduce chunk to {current_chunk}")
                time.sleep(2)
                continue
            raise

    for i, item in enumerate(items):
        item["text"] = translated_texts[i]
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
    if os.path.exists(partial_path):
        os.remove(partial_path)
    return True


def main():
    paths = glob.glob(DATASETS_GLOB)
    if not paths:
        print("No dialogueActs json files found.")
        return
    only_file = os.getenv("ONLY_FILE")
    if only_file:
        paths = [p for p in paths if os.path.basename(p).lower() == only_file.lower()]
        if not paths:
            print(f"No files matched ONLY_FILE={only_file}.")
            return
    force = os.getenv("FORCE")
    if force is not None:
        force = str(force).strip() not in ("", "0", "false", "False", "no", "No")
    chunk_size = os.getenv("CHUNK_SIZE")
    if chunk_size:
        try:
            chunk_size = int(chunk_size)
        except ValueError:
            chunk_size = None
    max_files = os.getenv("MAX_FILES")
    if max_files:
        try:
            max_files = int(max_files)
        except ValueError:
            max_files = None
    max_chunks = os.getenv("MAX_CHUNKS")
    if max_chunks:
        try:
            max_chunks = int(max_chunks)
        except ValueError:
            max_chunks = None
    max_seconds = os.getenv("MAX_SECONDS")
    if max_seconds:
        try:
            max_seconds = int(max_seconds)
        except ValueError:
            max_seconds = None
    print(f"Found {len(paths)} files.")
    count = 0
    for src in paths:
        rel = os.path.relpath(src, ROOT)
        parts = rel.split(os.sep)
        dataset_dir = parts[1]
        filename = parts[-1]
        dst = os.path.join(ROOT, "datasets", dataset_dir, "dialogueActs_kor", filename)
        if os.path.exists(dst) and not force:
            print(f"Skip (exists): {dst}")
            continue
        print(f"Translating {rel} -> {os.path.relpath(dst, ROOT)}")
        completed = translate_file(
            src,
            dst,
            chunk_size=chunk_size or 120,
            max_chunks=max_chunks,
            max_seconds=max_seconds,
        )
        count += 1
        if not completed:
            print("Partial saved; exiting to respect limits.")
            break
        if max_files and count >= max_files:
            print(f"Reached MAX_FILES={max_files}.")
            break
    print("Done.")


if __name__ == "__main__":
    main()
