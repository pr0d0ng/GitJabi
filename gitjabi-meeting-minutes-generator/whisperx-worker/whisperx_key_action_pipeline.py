import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import torch
from dotenv import load_dotenv
from huggingface_hub import HfApi
from omegaconf import DictConfig
from omegaconf.base import ContainerMetadata
from omegaconf.listconfig import ListConfig
from transformers import (
    AutoModelForCausalLM,
    AutoModelForSequenceClassification,
    AutoTokenizer,
)

# Allowlist objects required by some checkpoints when using PyTorch 2.6+
torch.serialization.add_safe_globals([
    Any,
    DictConfig,
    ListConfig,
    ContainerMetadata,
])

# PyTorch 2.6+ defaults torch.load(..., weights_only=True).
# WhisperX/pyannote checkpoints may require full checkpoint loading.
os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")

import whisperx


def parse_args(base_dir: Path, project_root: Path):
    # Runtime knobs are exposed via CLI so we can tune ASR/diarization
    # behavior without touching code.
    parser = argparse.ArgumentParser(
        description="WhisperX diarization + per-utterance key/action classification."
    )
    parser.add_argument("--audio", type=str, default=str(base_dir / "test_5min.wav"))
    parser.add_argument("--asr-model", type=str, default="medium")
    parser.add_argument("--language", type=str, default="ko")
    parser.add_argument("--compute-type", type=str, default=None)

    # ASR decode/VAD tuning
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--best-of", type=int, default=5)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--no-speech-threshold", type=float, default=0.3)
    parser.add_argument("--condition-on-previous-text", action="store_true")
    parser.add_argument("--vad-method", type=str, default="pyannote", choices=["pyannote", "silero"])
    parser.add_argument("--vad-onset", type=float, default=0.35)
    parser.add_argument("--vad-offset", type=float, default=0.2)
    parser.add_argument("--vad-chunk-size", type=int, default=30)
    parser.add_argument("--asr-chunk-seconds", type=float, default=0.0)

    # Diarization controls
    parser.add_argument("--num-speakers", type=int, default=None)
    parser.add_argument("--min-speakers", type=int, default=None)
    parser.add_argument("--max-speakers", type=int, default=None)

    # Existing fine-tuned models
    parser.add_argument(
        "--key-model-dir",
        type=str,
        default=str(project_root / "outputs" / "summary_worthy" / "best_model"),
    )
    parser.add_argument(
        "--action-model-dir",
        type=str,
        default=str(project_root / "outputs" / "has_action_item" / "best_model"),
    )
    parser.add_argument("--key-threshold", type=float, default=0.5)
    parser.add_argument("--action-threshold", type=float, default=0.5)
    parser.add_argument("--clf-max-length", type=int, default=256)
    parser.add_argument("--clf-batch-size", type=int, default=32)

    # Output
    parser.add_argument("--output-dir", type=str, default=str(base_dir / "out"))

    # Repeat dedupe
    parser.add_argument("--dedupe-short-repeats", action="store_true")
    parser.add_argument("--dedupe-max-segment-sec", type=float, default=1.2)
    parser.add_argument("--dedupe-max-gap-sec", type=float, default=0.35)
    parser.add_argument("--dedupe-min-run", type=int, default=3)

    # Laughter/hallucination block collapse
    parser.add_argument("--collapse-laughter-runs", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--laughter-min-repeats", type=int, default=4)
    parser.add_argument("--laughter-min-span-sec", type=float, default=5.0)
    parser.add_argument("--laughter-max-gap-sec", type=float, default=2.5)
    parser.add_argument("--trim-laughter-tail", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--laughter-tail-min-chars", type=int, default=12)

    # Context-based correction (non-rule, LM reranking)
    parser.add_argument("--context-correct", action="store_true")
    parser.add_argument("--context-lm-model", type=str, default="skt/kogpt2-base-v2")
    parser.add_argument("--context-min-token-freq", type=int, default=2)
    parser.add_argument("--context-max-candidates", type=int, default=8)
    parser.add_argument("--context-min-loss-improve", type=float, default=0.35)

    args = parser.parse_args()

    if args.num_speakers is not None and (
        args.min_speakers is not None or args.max_speakers is not None
    ):
        raise ValueError("Use either --num-speakers or (--min-speakers/--max-speakers), not both.")
    if (
        args.min_speakers is not None
        and args.max_speakers is not None
        and args.min_speakers > args.max_speakers
    ):
        raise ValueError("--min-speakers must be <= --max-speakers.")
    return args


def load_hf_token() -> str:
    load_dotenv()
    token = (
        os.getenv("HF_TOKEN")
        or os.getenv("HUGGINGFACE_TOKEN")
        or os.getenv("HF_HUB_TOKEN")
    )
    if not token:
        raise ValueError(
            "Hugging Face token not found. Set HF_TOKEN (or HUGGINGFACE_TOKEN / HF_HUB_TOKEN) in .env"
        )
    return token


def verify_hf_access(token: str) -> None:
    # Fail fast if gated pyannote models are not accessible.
    api = HfApi(token=token)
    try:
        api.whoami()
    except Exception as e:
        raise RuntimeError(
            "Hugging Face token is invalid or expired. Reissue a token with Read access."
        ) from e

    required_models = [
        "pyannote/speaker-diarization-3.1",
        "pyannote/segmentation-3.0",
    ]
    for model_id in required_models:
        try:
            api.model_info(model_id)
        except Exception as e:
            raise RuntimeError(
                f"No access to '{model_id}'. Accept model terms on Hugging Face and ensure token has Read scope."
            ) from e


def load_binary_classifier(model_dir: Path, device: torch.device):
    if not model_dir.exists():
        raise FileNotFoundError(f"Model dir not found: {model_dir}")
    tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
    model = model.to(device)
    model.eval()
    return tokenizer, model


def predict_positive_probs(
    texts,
    tokenizer,
    model,
    device: torch.device,
    max_length: int = 256,
    batch_size: int = 32,
):
    # Shared batched inference for binary classifiers.
    probs = []
    if not texts:
        return probs
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            enc = tokenizer(
                chunk,
                truncation=True,
                padding=True,
                max_length=max_length,
                return_tensors="pt",
            )
            enc = {k: v.to(device) for k, v in enc.items()}
            logits = model(**enc).logits
            p = torch.softmax(logits, dim=-1)[:, 1]
            probs.extend(p.detach().cpu().tolist())
    return probs


def build_diarize_kwargs(args):
    diarize_kwargs = {}
    if args.num_speakers is not None:
        diarize_kwargs["min_speakers"] = args.num_speakers
        diarize_kwargs["max_speakers"] = args.num_speakers
    else:
        if args.min_speakers is not None:
            diarize_kwargs["min_speakers"] = args.min_speakers
        if args.max_speakers is not None:
            diarize_kwargs["max_speakers"] = args.max_speakers
    return diarize_kwargs


def _norm_text(t: str) -> str:
    # Normalize surface form for repeat/hallucination matching.
    t = t.strip().lower()
    t = re.sub(r"[^0-9a-zA-Z가-힣]+", "", t)
    return t


def dedupe_short_repeat_utterances(
    utterances,
    max_segment_sec: float = 1.2,
    max_gap_sec: float = 0.35,
    min_run: int = 3,
):
    # Merge near-contiguous repeated short segments like "희희." runs.
    if not utterances:
        return utterances

    out = []
    i = 0
    while i < len(utterances):
        base = utterances[i]
        base_norm = _norm_text(base.get("text", ""))
        run = [base]
        j = i + 1
        while j < len(utterances):
            cur = utterances[j]
            cur_norm = _norm_text(cur.get("text", ""))
            prev = run[-1]
            prev_end = float(prev.get("end", 0.0))
            cur_start = float(cur.get("start", 0.0))
            cur_dur = float(cur.get("end", 0.0)) - cur_start
            if (
                base_norm
                and cur_norm == base_norm
                and cur_dur <= max_segment_sec
                and (cur_start - prev_end) <= max_gap_sec
            ):
                run.append(cur)
                j += 1
                continue
            break

        if len(run) >= min_run:
            merged = dict(run[0])
            merged["start"] = float(run[0]["start"])
            merged["end"] = float(run[-1]["end"])
            speaker = "UNKNOWN"
            for r in run:
                sp = r.get("speaker", "UNKNOWN")
                if sp != "UNKNOWN":
                    speaker = sp
                    break
            merged["speaker"] = speaker
            out.append(merged)
        else:
            out.extend(run)

        i = j

    for idx, utt in enumerate(out, start=1):
        utt["utt_id"] = idx
    return out


def _is_laughter_like(norm_text: str) -> bool:
    # Heuristic bucket for laughter-like tokens in KR/EN chat style.
    if not norm_text:
        return False
    if norm_text in {"haha", "hehe", "lol", "lmao"}:
        return True
    laughter_chars = set("하히헤허흐호후ㅋ")
    return all(ch in laughter_chars for ch in norm_text)


def collapse_laughter_hallucination_runs(
    utterances,
    min_repeats: int = 4,
    min_span_sec: float = 5.0,
    max_gap_sec: float = 2.5,
):
    # Collapse long laughter-dominated blocks to one placeholder segment.
    if not utterances:
        return utterances, []

    out = []
    suspicious_spans = []
    i = 0
    while i < len(utterances):
        first = utterances[i]
        first_norm = _norm_text(first.get("text", ""))
        if not _is_laughter_like(first_norm):
            out.append(first)
            i += 1
            continue

        run = [first]
        run_norms = [first_norm]
        j = i + 1
        while j < len(utterances):
            prev = run[-1]
            cur = utterances[j]
            gap = float(cur.get("start", 0.0)) - float(prev.get("end", 0.0))
            cur_norm = _norm_text(cur.get("text", ""))
            if gap <= max_gap_sec and _is_laughter_like(cur_norm):
                run.append(cur)
                run_norms.append(cur_norm)
                j += 1
                continue
            break

        run_start = float(run[0].get("start", 0.0))
        run_end = float(run[-1].get("end", 0.0))
        run_span = run_end - run_start
        laughter_ratio = sum(1 for n in run_norms if _is_laughter_like(n)) / max(len(run_norms), 1)

        should_collapse = (
            len(run) >= min_repeats
            and run_span >= min_span_sec
            and laughter_ratio >= 0.9
        )

        if should_collapse:
            speaker = "UNKNOWN"
            for r in run:
                sp = r.get("speaker", "UNKNOWN")
                if sp != "UNKNOWN":
                    speaker = sp
                    break
            out.append(
                {
                    "utt_id": 0,
                    "start": run_start,
                    "end": run_end,
                    "speaker": speaker,
                    "text": "[LAUGHTER_OR_HALLUCINATION_BLOCK]",
                    "hallucination_flag": True,
                }
            )
            suspicious_spans.append(
                {
                    "start": run_start,
                    "end": run_end,
                    "n_segments": len(run),
                    "kind": "laughter_repetition_block",
                }
            )
        else:
            out.extend(run)

        i = j

    for idx, utt in enumerate(out, start=1):
        utt["utt_id"] = idx
    return out, suspicious_spans


def trim_laughter_tail(text: str, min_chars: int = 12):
    # Remove trailing laughter tails from a single utterance text.
    cleaned = text.replace("\ufffd", "").strip()
    pat = re.compile(rf"([흐하히헤허ㅋ]\s*){{{min_chars},}}$")
    m = pat.search(cleaned)
    if not m:
        return cleaned, False
    trimmed = cleaned[: m.start()].rstrip(" .,!?:;~")
    if len(trimmed) < 4:
        return cleaned, False
    return trimmed, True


def _is_hangul_token(tok: str) -> bool:
    return bool(re.fullmatch(r"[가-힣]{2,}", tok))


def _tokenize_ws(text: str):
    return [t for t in text.split() if t.strip()]


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            ins = cur[j - 1] + 1
            dele = prev[j] + 1
            sub = prev[j - 1] + (ca != cb)
            cur.append(min(ins, dele, sub))
        prev = cur
    return prev[-1]


def _sent_nll(text: str, tok, lm, device: torch.device) -> float:
    enc = tok(text, return_tensors="pt", truncation=True, max_length=256)
    enc = {k: v.to(device) for k, v in enc.items()}
    with torch.no_grad():
        out = lm(**enc, labels=enc["input_ids"])
    return float(out.loss.detach().cpu().item())


def _build_token_vocab(utterances, min_freq: int = 2):
    freq = {}
    for u in utterances:
        for t in _tokenize_ws(str(u.get("text", ""))):
            if _is_hangul_token(t):
                freq[t] = freq.get(t, 0) + 1
    vocab = {k for k, v in freq.items() if v >= min_freq}
    return freq, vocab


def _candidates_for_token(token: str, vocab, freq, max_candidates: int = 8):
    cands = []
    for v in vocab:
        if v == token:
            continue
        if abs(len(v) - len(token)) > 2:
            continue
        if not v or v[0] != token[0]:
            continue
        d = _levenshtein(token, v)
        if d <= 2:
            cands.append((d, -freq.get(v, 0), v))
    cands.sort()
    return [v for _, _, v in cands[:max_candidates]]


def apply_context_correction(
    utterances,
    device: torch.device,
    lm_model_name: str = "skt/kogpt2-base-v2",
    min_token_freq: int = 2,
    max_candidates: int = 8,
    min_loss_improve: float = 0.35,
):
    # Non-rule contextual correction:
    # compare sentence loss before/after candidate substitutions and
    # keep only changes with sufficient improvement margin.
    if not utterances:
        return utterances, 0

    tok = AutoTokenizer.from_pretrained(lm_model_name)
    lm = AutoModelForCausalLM.from_pretrained(lm_model_name).to(device)
    lm.eval()

    freq, vocab = _build_token_vocab(utterances, min_freq=min_token_freq)
    changed = 0

    for utt in utterances:
        text = str(utt.get("text", "")).strip()
        toks = _tokenize_ws(text)
        if not toks:
            continue

        base_loss = _sent_nll(text, tok, lm, device)
        best_loss = base_loss
        best_text = text
        best_meta = None

        for i, tk in enumerate(toks):
            if not _is_hangul_token(tk):
                continue
            if freq.get(tk, 0) >= min_token_freq:
                continue

            cands = _candidates_for_token(
                tk, vocab=vocab, freq=freq, max_candidates=max_candidates
            )
            for cand in cands:
                cand_toks = list(toks)
                cand_toks[i] = cand
                cand_text = " ".join(cand_toks)
                cand_loss = _sent_nll(cand_text, tok, lm, device)
                if cand_loss < best_loss:
                    best_loss = cand_loss
                    best_text = cand_text
                    best_meta = {"from": tk, "to": cand, "token_index": i}

        if best_text != text and (base_loss - best_loss) >= min_loss_improve:
            utt["raw_text"] = text
            utt["text"] = best_text
            utt["context_corrected"] = True
            utt["context_correction"] = best_meta
            utt["context_loss_before"] = round(base_loss, 4)
            utt["context_loss_after"] = round(best_loss, 4)
            changed += 1

    return utterances, changed


def main():
    base_dir = Path(__file__).resolve().parent
    project_root = base_dir.parent
    args = parse_args(base_dir, project_root)

    hf_token = load_hf_token()
    verify_hf_access(hf_token)

    device_name = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device_name)
    compute_type = args.compute_type or ("float16" if device_name == "cuda" else "int8")
    print("Device:", device_name)
    print("Compute type:", compute_type)

    audio_file = Path(args.audio).expanduser().resolve()
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file}")
    audio_path = str(audio_file)

    start = time.time()

    asr_options = {
        "beam_size": args.beam_size,
        "best_of": args.best_of,
        "temperatures": [args.temperature],
        "no_speech_threshold": args.no_speech_threshold,
        "condition_on_previous_text": args.condition_on_previous_text,
    }
    vad_options = {
        "chunk_size": args.vad_chunk_size,
        "vad_onset": args.vad_onset,
        "vad_offset": args.vad_offset,
    }
    print("ASR options:", asr_options)
    print("ASR VAD options:", {"vad_method": args.vad_method, **vad_options})

    asr_model = whisperx.load_model(
        args.asr_model,
        device=device_name,
        compute_type=compute_type,
        language=args.language,
        asr_options=asr_options,
        vad_method=args.vad_method,
        vad_options=vad_options,
    )

    # WhisperX API differs by version; keep a safe compatibility wrapper.
    def _transcribe_once(audio_input):
        try:
            return asr_model.transcribe(audio_input, language=args.language)
        except TypeError:
            return asr_model.transcribe(audio_input)

    if args.asr_chunk_seconds and args.asr_chunk_seconds > 0:
        # Chunked ASR helps break decoding loops/hallucination lock-in.
        print("ASR chunk mode:", args.asr_chunk_seconds, "sec")
        waveform = whisperx.load_audio(audio_path)
        sample_rate = 16000
        total_sec = len(waveform) / sample_rate
        chunk_samples = int(args.asr_chunk_seconds * sample_rate)
        all_segments = []
        detected_language = args.language
        chunk_idx = 0

        for start_sample in range(0, len(waveform), chunk_samples):
            end_sample = min(start_sample + chunk_samples, len(waveform))
            chunk_audio = waveform[start_sample:end_sample]
            offset_sec = start_sample / sample_rate
            chunk_idx += 1
            print(f"ASR chunk {chunk_idx}: {offset_sec:.1f}~{end_sample/sample_rate:.1f}s")
            chunk_result = _transcribe_once(chunk_audio)
            if chunk_result.get("language"):
                detected_language = chunk_result["language"]
            for seg in chunk_result.get("segments", []):
                seg = dict(seg)
                seg["start"] = float(seg.get("start", 0.0)) + offset_sec
                seg["end"] = float(seg.get("end", 0.0)) + offset_sec
                all_segments.append(seg)

        asr_result = {"language": detected_language, "segments": all_segments}
        print(f"ASR chunk mode done: total={total_sec:.1f}s, segments={len(all_segments)}")
    else:
        asr_result = _transcribe_once(audio_path)

    model_a, metadata = whisperx.load_align_model(
        language_code=asr_result["language"],
        device=device_name,
    )
    aligned_result = whisperx.align(
        asr_result["segments"],
        model_a,
        metadata,
        audio_path,
        device_name,
    )

    diarize_model = whisperx.diarize.DiarizationPipeline(
        use_auth_token=hf_token,
        device=device_name,
        model_name="pyannote/speaker-diarization-3.1",
    )
    diarize_kwargs = build_diarize_kwargs(args)
    if diarize_kwargs:
        print("Diarization speaker constraints:", diarize_kwargs)
    else:
        print("Diarization speaker constraints: auto")
    diarize_segments = diarize_model(audio_path, **diarize_kwargs)

    merged_result = whisperx.assign_word_speakers(
        diarize_segments,
        aligned_result,
    )

    # Build utterance-level rows (time/speaker/text) for downstream scoring.
    utterances = []
    for idx, seg in enumerate(merged_result.get("segments", []), start=1):
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        utterances.append(
            {
                "utt_id": idx,
                "start": float(seg.get("start", 0.0)),
                "end": float(seg.get("end", 0.0)),
                "speaker": seg.get("speaker", "UNKNOWN"),
                "text": text,
            }
        )

    if args.dedupe_short_repeats:
        before_n = len(utterances)
        utterances = dedupe_short_repeat_utterances(
            utterances,
            max_segment_sec=args.dedupe_max_segment_sec,
            max_gap_sec=args.dedupe_max_gap_sec,
            min_run=args.dedupe_min_run,
        )
        print("Dedupe short repeats:", before_n, "->", len(utterances))

    suspicious_spans = []
    if args.collapse_laughter_runs:
        before_n = len(utterances)
        utterances, suspicious_spans = collapse_laughter_hallucination_runs(
            utterances,
            min_repeats=args.laughter_min_repeats,
            min_span_sec=args.laughter_min_span_sec,
            max_gap_sec=args.laughter_max_gap_sec,
        )
        print("Collapse laughter runs:", before_n, "->", len(utterances))
        if suspicious_spans:
            print("Suspicious spans:", suspicious_spans)

    if args.trim_laughter_tail:
        trimmed_count = 0
        for utt in utterances:
            original = utt.get("text", "")
            trimmed, changed = trim_laughter_tail(
                original,
                min_chars=args.laughter_tail_min_chars,
            )
            if changed:
                utt["raw_text"] = original
                utt["text"] = trimmed
                utt["hallucination_flag"] = True
                utt["hallucination_kind"] = "laughter_tail_trimmed"
                trimmed_count += 1
        if trimmed_count:
            print("Trimmed laughter tails:", trimmed_count)

    if args.context_correct:
        print("Context correction model:", args.context_lm_model)
        utterances, n_changed = apply_context_correction(
            utterances,
            device=device,
            lm_model_name=args.context_lm_model,
            min_token_freq=args.context_min_token_freq,
            max_candidates=args.context_max_candidates,
            min_loss_improve=args.context_min_loss_improve,
        )
        print("Context-corrected utterances:", n_changed)

    key_model_dir = Path(args.key_model_dir).resolve()
    action_model_dir = Path(args.action_model_dir).resolve()
    key_tokenizer, key_model = load_binary_classifier(key_model_dir, device)
    action_tokenizer, action_model = load_binary_classifier(action_model_dir, device)

    texts = [u["text"] for u in utterances]
    key_probs = predict_positive_probs(
        texts,
        key_tokenizer,
        key_model,
        device=device,
        max_length=args.clf_max_length,
        batch_size=args.clf_batch_size,
    )
    action_probs = predict_positive_probs(
        texts,
        action_tokenizer,
        action_model,
        device=device,
        max_length=args.clf_max_length,
        batch_size=args.clf_batch_size,
    )

    counts = {"action": 0, "key": 0, "other": 0}
    # Final class policy: action > key > other.
    for i, utt in enumerate(utterances):
        key_prob = float(key_probs[i]) if i < len(key_probs) else 0.0
        action_prob = float(action_probs[i]) if i < len(action_probs) else 0.0

        is_key = key_prob >= args.key_threshold
        is_action = action_prob >= args.action_threshold

        if is_action:
            line_class = "action"
        elif is_key:
            line_class = "key"
        else:
            line_class = "other"
        counts[line_class] += 1

        utt["key_prob"] = round(key_prob, 6)
        utt["action_prob"] = round(action_prob, 6)
        utt["is_key"] = bool(is_key)
        utt["is_action"] = bool(is_action)
        utt["line_class"] = line_class

    elapsed = round(time.time() - start, 2)

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = audio_file.stem
    jsonl_path = output_dir / f"{stem}.key_action.jsonl"
    json_path = output_dir / f"{stem}.key_action.json"

    with open(jsonl_path, "w", encoding="utf-8") as f:
        for utt in utterances:
            f.write(json.dumps(utt, ensure_ascii=False) + "\n")

    payload = {
        "audio_file": str(audio_file),
        "language": asr_result.get("language"),
        "device": device_name,
        "compute_type": compute_type,
        "speaker_constraints": diarize_kwargs if diarize_kwargs else "auto",
        "model_dirs": {
            "key_model_dir": str(key_model_dir),
            "action_model_dir": str(action_model_dir),
        },
        "thresholds": {
            "key_threshold": args.key_threshold,
            "action_threshold": args.action_threshold,
        },
        "counts": counts,
        "suspicious_spans": suspicious_spans,
        "n_utterances": len(utterances),
        "elapsed_sec": elapsed,
        "utterances": utterances,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("Saved JSONL:", jsonl_path)
    print("Saved JSON:", json_path)
    print("Class counts:", counts)
    print("Elapsed:", elapsed, "sec")


if __name__ == "__main__":
    main()
