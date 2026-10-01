import glob
import json
import os
import re
import time
import urllib.error
import urllib.request


ROOT = os.path.abspath(os.getcwd())
DATASETS_GLOB = os.path.join(ROOT, "datasets", "*", "dialogueActs", "*.json")


def _load_dotenv(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().strip('"').strip("'")
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def _protect_tags(text):
    tags = re.findall(r"<[^>]+>", text)
    mapping = {}
    protected = text
    for i, tag in enumerate(tags):
        token = f"\uE000TAG{i}\uE001"
        mapping[token] = tag
        protected = protected.replace(tag, token)
    return protected, mapping


def _restore_tags(text, mapping):
    restored = text
    for token, tag in mapping.items():
        restored = restored.replace(token, tag)
    return restored


def _contains_cjk(text):
    if not isinstance(text, str):
        return False
    for ch in text:
        code = ord(ch)
        if 0x4E00 <= code <= 0x9FFF:
            return True
    return False


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
    state = {"translated_texts": translated_texts, "idx": idx}
    tmp_path = partial_path + ".tmp"
    for attempt in range(5):
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False)
            os.replace(tmp_path, partial_path)
            return
        except PermissionError:
            time.sleep(0.2 * (attempt + 1))
    with open(partial_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def _remove_partial(partial_path):
    if not os.path.exists(partial_path):
        return
    for attempt in range(5):
        try:
            os.remove(partial_path)
            return
        except PermissionError:
            time.sleep(0.2 * (attempt + 1))


def _post_json(url, payload, timeout=120):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw)


def _env_bool(name, default=False):
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def _env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_float(name, default):
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def _extract_assistant_content(data):
    return data["choices"][0]["message"]["content"].strip()


def _extract_json_array(content):
    content = content.strip()
    decoder = json.JSONDecoder()
    for i, ch in enumerate(content):
        if ch != "[":
            continue
        try:
            obj, _ = decoder.raw_decode(content[i:])
            if isinstance(obj, list):
                return obj
        except Exception:
            continue
    raise ValueError("No JSON array found in model output")


def _extract_single_text(content):
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text).strip()
    # If model accidentally returned JSON array/string, decode it.
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list) and parsed:
            return str(parsed[0]).strip()
        if isinstance(parsed, str):
            return parsed.strip()
    except Exception:
        pass
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        try:
            return json.loads(text)
        except Exception:
            pass
    return text.strip()


def _build_system_prompt(strict=False):
    prompt = (
        "You are a professional EN->KO meeting translator. "
        "Translate each English utterance into natural Korean spoken in real meetings by native speakers. "
        "Prefer idiomatic Korean over literal wording. "
        "Keep fillers natural (um/uh -> Korean fillers). "
        "Use concise conversational style and polite endings when appropriate. "
        "Preserve placeholders like \\uE000TAG0\\uE001 exactly. "
        "Keep order and count exactly the same. "
        "Input may be either an array of strings or an array of objects with keys "
        "'context' (previous utterances) and 'text' (current utterance). "
        "Use context only for disambiguation and translate only the current 'text'. "
        "Return ONLY a JSON array of strings."
    )
    if strict:
        prompt += (
            " Hard constraints: "
            "1) No English words in output unless they are proper nouns or product acronyms in the source. "
            "2) Do not output transliteration artifacts like alRIGHT or mixed-language tokens. "
            "3) Translate short discourse words naturally: Okay/Right/Great/Yeah -> Korean equivalents. "
            "4) Never use awkward literal forms for simple acknowledgements. "
            "5) Do not omit any item. No extra commentary."
        )
    return prompt


def _build_single_text_prompt():
    return (
        "You are a professional EN->KO meeting translator. "
        "Translate exactly one English utterance into natural Korean spoken in meetings. "
        "You may receive optional previous utterances as context. "
        "Use them only to disambiguate the current sentence. "
        "Preserve placeholders like \\uE000TAG0\\uE001 exactly. "
        "Return ONLY the translated Korean sentence as plain text, not JSON."
    )


def _contains_ascii_letters(text):
    return any(("A" <= ch <= "Z") or ("a" <= ch <= "z") for ch in text)


def _has_forbidden_script(text):
    if not isinstance(text, str):
        return True
    # Disallow scripts that should not appear in Korean output.
    if re.search(r"[\u0400-\u052f]", text):  # Cyrillic
        return True
    if re.search(r"[\u3040-\u30ff\u31f0-\u31ff]", text):  # Hiragana/Katakana
        return True
    if re.search(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", text):  # CJK ideographs
        return True
    return False


def _strip_tags(text):
    return re.sub(r"<[^>]+>", "", text)


def _normalize_for_match(text):
    text = _strip_tags(text).lower().strip()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _looks_low_quality(src, tgt):
    src_norm = _strip_tags(src).strip()
    tgt_norm = _strip_tags(tgt).strip()
    if not src_norm and not tgt_norm:
        return False
    if src_norm and not tgt_norm:
        return True
    if re.fullmatch(r"[\s,.;:!?-]*", tgt_norm):
        return True
    bad_patterns = ("alright", "indeed", "kinda", "uh ", " um ", "\uad7f\uc785\ub2c8\ub2e4")
    lowered = tgt_norm.lower()
    if any(p in lowered for p in bad_patterns):
        return True
    if re.search(r"\uE000TAG\d+\uE001", tgt):
        return True
    if re.search(r"[가-힣]+[A-Za-z]{2,}", tgt):
        return True
    if _has_forbidden_script(tgt):
        return True
    if _contains_ascii_letters(tgt_norm):
        src_words = set(re.findall(r"[A-Za-z]+", src_norm.lower()))
        tgt_words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", tgt_norm)
        allowed_acronyms = {"tv", "vcr", "dvd", "cd", "ui", "id", "pm", "mp3"}
        bad_words = []
        for w in tgt_words:
            wl = w.lower()
            if len(wl) == 1:
                continue
            if wl in allowed_acronyms:
                continue
            # Allow a single proper noun copied from source, e.g. Laura/David.
            if len(tgt_words) == 1 and w[:1].isupper() and wl in src_words:
                continue
            bad_words.append(w)
        if bad_words:
            return True
    return False


def _fallback_short_utterance(src_text, translated_text):
    src_norm = _normalize_for_match(src_text)
    short_map = {
        "okay": "\uc54c\uaca0\uc2b5\ub2c8\ub2e4.",
        "ok": "\uc54c\uaca0\uc2b5\ub2c8\ub2e4.",
        "right": "\ub9de\uc544\uc694.",
        "all right": "\uc88b\uc544\uc694.",
        "alright": "\uc88b\uc544\uc694.",
        "great": "\uc88b\ub124\uc694.",
        "yeah": "\ub124.",
        "yep": "\ub124.",
        "mm hmm": "\ub124.",
        "uh huh": "\ub124.",
        "hmm": "\uc74c.",
        "sorry": "\ub124? \uc8c4\uc1a1\ud55c\ub370 \ub2e4\uc2dc \ub9d0\uc500\ud574 \uc8fc\uc2dc\uaca0\uc5b4\uc694?",
        "pardon": "\ub124? \ub2e4\uc2dc \ub9d0\uc500\ud574 \uc8fc\uc2dc\uaca0\uc5b4\uc694?",
    }
    if src_norm in short_map:
        return short_map[src_norm]

    fixed = translated_text
    fixed = re.sub(r"알\s*RIGHT", "\uc54c\uaca0\uc2b5\ub2c8\ub2e4", fixed, flags=re.IGNORECASE)
    fixed = fixed.replace("\uad7f\uc785\ub2c8\ub2e4", "\uc88b\uc544\uc694")
    fixed = fixed.replace("\uc608\uc058\uc694", "\uc88b\uc544\uc694")
    fixed = fixed.replace("리테이ラー", "리테일러")
    return fixed


def _make_user_input(texts, contexts=None):
    if not contexts:
        return json.dumps(texts, ensure_ascii=False)
    payload_items = []
    for t, c in zip(texts, contexts):
        payload_items.append({"context": c or [], "text": t})
    return json.dumps(payload_items, ensure_ascii=False)


def _call_llama_cpp(base_url, texts, max_retries=None, strict=False, contexts=None):
    if max_retries is None:
        max_retries = _env_int("MAX_RETRIES_BATCH", 2)
    request_timeout = _env_int("REQUEST_TIMEOUT", 45)
    retry_sleep = _env_float("RETRY_SLEEP", 0.5)
    system_prompt = _build_system_prompt(strict=strict)
    user_prompt = _make_user_input(texts, contexts=contexts)
    payload = {
        "model": "local",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1 if strict else 0.2,
    }
    last_err = None
    for attempt in range(max_retries):
        try:
            data = _post_json(
                f"{base_url}/v1/chat/completions", payload, timeout=request_timeout
            )
            content = _extract_assistant_content(data)
            translated = _extract_json_array(content)
            if not isinstance(translated, list) or len(translated) != len(texts):
                last_err = f"Length mismatch. got {len(translated)} expected {len(texts)}"
                time.sleep(retry_sleep * (attempt + 1))
                continue
            if not all(isinstance(t, str) for t in translated):
                last_err = "Non-string item detected in output array."
                time.sleep(retry_sleep * (attempt + 1))
                continue
            if any(_contains_cjk(t) for t in translated):
                last_err = "CJK characters detected in output."
                time.sleep(retry_sleep * (attempt + 1))
                continue
            return translated
        except Exception as e:
            last_err = str(e)
            time.sleep(retry_sleep * (attempt + 1))
    raise RuntimeError(last_err or "Unknown error")


def _call_llama_cpp_single_text(base_url, text, max_retries=None, context=None):
    if max_retries is None:
        max_retries = _env_int("MAX_RETRIES_SINGLE", 2)
    request_timeout = _env_int("REQUEST_TIMEOUT", 45)
    retry_sleep = _env_float("RETRY_SLEEP", 0.5)
    system_prompt = _build_single_text_prompt()
    user_payload = {"context": context or [], "text": text}
    payload = {
        "model": "local",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        "temperature": 0.1,
    }
    last_err = None
    for attempt in range(max_retries):
        try:
            data = _post_json(
                f"{base_url}/v1/chat/completions", payload, timeout=request_timeout
            )
            content = _extract_assistant_content(data)
            out = _extract_single_text(content)
            if _has_forbidden_script(out):
                last_err = "Forbidden script detected in single-text output."
                time.sleep(retry_sleep * (attempt + 1))
                continue
            if out:
                return out
            last_err = "Empty text output"
            time.sleep(retry_sleep * (attempt + 1))
        except Exception as e:
            last_err = str(e)
            time.sleep(retry_sleep * (attempt + 1))
    raise RuntimeError(last_err or "Unknown error")


def _retranslate_if_needed(base_url, src_text, translated_text, context=None):
    fast_mode = _env_bool("FAST_MODE", False)
    quality_retry = _env_bool("ENABLE_QUALITY_RETRY", True)
    if fast_mode or not quality_retry:
        quick = _fallback_short_utterance(src_text, translated_text)
        if _has_forbidden_script(quick):
            pt, mp = _protect_tags(src_text)
            try:
                fixed = _call_llama_cpp(base_url, [pt], max_retries=1, strict=True, contexts=[context or []])[0]
            except RuntimeError:
                try:
                    fixed = _call_llama_cpp_single_text(base_url, pt, max_retries=1, context=context)
                except RuntimeError:
                    return quick
            fixed = _restore_tags(fixed, mp)
            return _fallback_short_utterance(src_text, fixed)
        return quick
    translated_text = _fallback_short_utterance(src_text, translated_text)
    if not _looks_low_quality(src_text, translated_text):
        return translated_text
    pt, mp = _protect_tags(src_text)
    for _ in range(2):
        try:
            retried = _call_llama_cpp(
                base_url, [pt], max_retries=3, strict=True, contexts=[context or []]
            )[0]
        except RuntimeError:
            retried = _call_llama_cpp_single_text(base_url, pt, max_retries=3, context=context)
        restored = _restore_tags(retried, mp)
        restored = _fallback_short_utterance(src_text, restored)
        if not _looks_low_quality(src_text, restored):
            return restored
        translated_text = restored
    return _fallback_short_utterance(src_text, translated_text)


def _translate_batch_with_fallback(base_url, protected_batch, contexts=None):
    fast_mode = _env_bool("FAST_MODE", False)
    try:
        return _call_llama_cpp(base_url, protected_batch, contexts=contexts)
    except RuntimeError:
        out = []
        for i, text in enumerate(protected_batch):
            ctx = contexts[i] if contexts and i < len(contexts) else []
            try:
                out.append(
                    _call_llama_cpp(
                        base_url, [text], strict=(not fast_mode), contexts=[ctx]
                    )[0]
                )
            except RuntimeError:
                out.append(_call_llama_cpp_single_text(base_url, text, max_retries=3, context=ctx))
        return out


def translate_file(
    src_path,
    dst_path,
    base_url,
    batch_size=16,
    context_window=2,
    recheck_prior=False,
    max_prior_recheck=50,
):
    with open(src_path, "r", encoding="utf-8") as f:
        items = json.load(f)
    texts = [item.get("text", "") for item in items]
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    partial_path = dst_path + ".partial.json"
    state = _load_partial(partial_path, len(texts))
    if state:
        translated_texts = state["translated_texts"]
        idx = state["idx"]
        fixed = 0
        for i in range(idx):
            corrected = _fallback_short_utterance(texts[i], translated_texts[i])
            if corrected != translated_texts[i]:
                translated_texts[i] = corrected
                fixed += 1
        if recheck_prior and idx > 0:
            rechecked = 0
            for i in range(idx):
                if rechecked >= max_prior_recheck:
                    break
                src_text = texts[i]
                tgt_text = translated_texts[i]
                if not _looks_low_quality(src_text, tgt_text):
                    continue
                start = max(0, i - max(0, context_window))
                context = texts[start:i]
                translated_texts[i] = _retranslate_if_needed(
                    base_url, src_text, tgt_text, context=context
                )
                rechecked += 1
            if rechecked:
                fixed += rechecked
        if fixed:
            _save_partial(partial_path, translated_texts, idx)
            print(f"  normalized {fixed} prior items")
        print(f"  resume from {idx}/{len(texts)}")
    else:
        translated_texts = [""] * len(texts)
        idx = 0

    while idx < len(texts):
        batch = texts[idx : idx + batch_size]
        protected = []
        maps = []
        contexts = []
        for t in batch:
            pt, mp = _protect_tags(t)
            protected.append(pt)
            maps.append(mp)
        for j in range(len(batch)):
            abs_idx = idx + j
            start = max(0, abs_idx - max(0, context_window))
            contexts.append(texts[start:abs_idx])

        translated = _translate_batch_with_fallback(base_url, protected, contexts=contexts)
        restored = [_restore_tags(tr, mp) for tr, mp in zip(translated, maps)]
        retried_count = 0
        for j, src_text in enumerate(batch):
            improved = _retranslate_if_needed(base_url, src_text, restored[j], context=contexts[j])
            if improved != restored[j]:
                retried_count += 1
                restored[j] = improved
        translated_texts[idx : idx + batch_size] = restored
        idx += batch_size
        _save_partial(partial_path, translated_texts, idx)
        msg = f"  translated {min(idx, len(texts))}/{len(texts)}"
        if retried_count:
            msg += f" (retried {retried_count})"
        print(msg)

    for i, item in enumerate(items):
        item["text"] = translated_texts[i]
    with open(dst_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
    _remove_partial(partial_path)


def main():
    _load_dotenv(os.path.join(ROOT, ".env"))
    base_url = os.getenv("LLAMA_CPP_URL", "http://127.0.0.1:8080")
    output_dirname = os.getenv("OUTPUT_DIRNAME", "dialogueActs_kor")
    only_file = os.getenv("ONLY_FILE")
    batch_size = int(os.getenv("BATCH_SIZE", "16"))
    context_window = int(os.getenv("CONTEXT_WINDOW", "2"))
    recheck_prior = os.getenv("RECHECK_PRIOR", "1").strip() == "1"
    max_prior_recheck = int(os.getenv("MAX_PRIOR_RECHECK", "50"))

    paths = glob.glob(DATASETS_GLOB)
    if only_file:
        paths = [p for p in paths if os.path.basename(p).lower() == only_file.lower()]
        if not paths:
            print(f"No files matched ONLY_FILE={only_file}.")
            return
    paths.sort()

    for src in paths:
        rel = os.path.relpath(src, ROOT)
        parts = rel.split(os.sep)
        dataset_dir = parts[1]
        filename = parts[-1]
        dst = os.path.join(ROOT, "datasets", dataset_dir, output_dirname, filename)
        if os.path.exists(dst):
            print(f"Skip (exists): {dst}")
            _remove_partial(dst + ".partial.json")
            continue
        print(f"Translating {rel} -> {os.path.relpath(dst, ROOT)}")
        translate_file(
            src,
            dst,
            base_url,
            batch_size=batch_size,
            context_window=context_window,
            recheck_prior=recheck_prior,
            max_prior_recheck=max_prior_recheck,
        )


if __name__ == "__main__":
    main()
