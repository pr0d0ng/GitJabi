import os
import json
import glob
import time
import re

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


ROOT = os.path.abspath(os.getcwd())
DATASETS_GLOB = os.path.join(ROOT, "datasets", "*", "dialogueActs", "*.json")


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
    for ch in text:
        code = ord(ch)
        if 0x4E00 <= code <= 0x9FFF:
            return True
    return False


def _postprocess_spoken(text):
    rules = [
        (r"???\.", "???."),
        (r"???\?", "????"),
        (r"???\.", "??."),
        (r"???\?", "???"),
        (r"???\.", "??."),
        (r"???\?", "???"),
        (r"????\.", "???."),
        (r"????\?", "????"),
        (r"????\.", "???."),
        (r"????\?", "????"),
        (r"????\.", "???."),
        (r"????\?", "????"),
    ]
    out = text
    for pattern, repl in rules:
        out = re.sub(pattern, repl, out)
    return out



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


def _translate_batch(model, tokenizer, texts, device, max_new_tokens):
    inputs = tokenizer(texts, return_tensors="pt", padding=True, truncation=True).to(device)
    outputs = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        num_beams=4,
        no_repeat_ngram_size=3,
        repetition_penalty=1.05,
    )
    return tokenizer.batch_decode(outputs, skip_special_tokens=True)


def _translate_with_retry(model, tokenizer, texts, device, max_new_tokens):
    translated = _translate_batch(model, tokenizer, texts, device, max_new_tokens)
    if any(_contains_cjk(t) for t in translated):
        fixed = []
        for t in texts:
            one = _translate_batch(model, tokenizer, [t], device, max_new_tokens)[0]
            fixed.append(one)
        translated = fixed
    return translated


def translate_file(
    src_path,
    dst_path,
    model,
    tokenizer,
    device,
    batch_size=16,
    max_new_tokens=128,
    style="",
    target_token="",
):
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

    while idx < len(texts):
        batch = texts[idx : idx + batch_size]
        if target_token:
            batch = [f"{target_token} {t}" for t in batch]
        protected = []
        maps = []
        for t in batch:
            pt, mp = _protect_tags(t)
            protected.append(pt)
            maps.append(mp)

        translated = _translate_with_retry(model, tokenizer, protected, device, max_new_tokens)
        restored = [_restore_tags(tr, mp) for tr, mp in zip(translated, maps)]
        if style == "spoken_polite":
            restored = [_postprocess_spoken(t) for t in restored]

        translated_texts[idx : idx + batch_size] = restored
        idx += batch_size
        _save_partial(partial_path, translated_texts, idx)
        print(f"  translated {min(idx, len(texts))}/{len(texts)}")

    for i, item in enumerate(items):
        item["text"] = translated_texts[i]
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
    if os.path.exists(partial_path):
        os.remove(partial_path)


def main():
    _load_dotenv(os.path.join(ROOT, ".env"))
    model_name = os.getenv("HF_MODEL", "Helsinki-NLP/opus-mt-tc-big-en-ko")
    if model_name.startswith("HF_MODEL="):
        model_name = model_name.split("=", 1)[1]
    hf_token = os.getenv("HF_TOKEN", "").strip() or None
    output_dirname = os.getenv("OUTPUT_DIRNAME", "dialogueActs_kor")
    only_file = os.getenv("ONLY_FILE")
    batch_size = int(os.getenv("BATCH_SIZE", "16"))
    max_new_tokens = int(os.getenv("MAX_NEW_TOKENS", "128"))
    style = os.getenv("STYLE", "").strip()
    target_lang = os.getenv("TARGET_LANG", "").strip()
    target_token = f">>{target_lang}<<" if target_lang else ""

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device: {device}")
    print(f"model: {model_name}")

    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True, token=hf_token)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name, token=hf_token).to(device)

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
            continue
        print(f"Translating {rel} -> {os.path.relpath(dst, ROOT)}")
        translate_file(
            src,
            dst,
            model,
            tokenizer,
            device,
            batch_size=batch_size,
            max_new_tokens=max_new_tokens,
            style=style,
            target_token=target_token,
        )


if __name__ == "__main__":
    main()
