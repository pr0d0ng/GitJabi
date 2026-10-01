import argparse
import glob
import json
import os
import re
from collections import Counter
from typing import Dict, List, Set, Tuple


LABEL_MAP = {"OTHER": 0, "KEY": 1, "ACTION": 2}


AMI_NON_KEY = {"ass", "bck", "stl", "fra", "und", "el.ass", "oth"}
AMI_KEY_HINT = {"inf", "el.inf", "off", "sug", "el.sug", "be.pos", "be.neg"}

# ICSI/MRDA-ish coarse hints by top token (before separators)
ICSI_NON_KEY_PREFIX = {"b", "h", "fh", "z", "%", "x"}
ICSI_KEY_PREFIX = {"s", "qy", "qw", "qo", "qr", "qrr"}
ICSI_NON_KEY_SUBTAGS = {"bk", "aa", "na", "no", "ng", "nd", "rt", "e"}


ACTION_PATTERNS = [
    r"\b(action item|todo|to-do)\b",
    r"\b(should|must|need to|needs to|have to|has to)\b",
    r"\b(let's|let us)\b",
    r"\b(i will|i'll|we will|we'll)\b",
    r"\b(please)\b",
    r"\b(by (monday|tuesday|wednesday|thursday|friday|tomorrow|next week))\b",
    # Korean action/commitment cues
    r"(해야|하겠습니다|하자|해요|해 주세요|해주세요|부탁|담당|까지|다음 회의 전|액션 아이템|할 일)",
    r"(겠습니다|할게요|해둘게요|넣을게요|정리할게요|보낼게요|올릴게요|공유할게요|포함시키겠습니다)",
]
ACTION_RE = re.compile("|".join(ACTION_PATTERNS), flags=re.IGNORECASE)

REQUEST_PATTERNS = [
    r"(받을 수 있|\bcan i get\b|\bcould i get\b)",
    r"(공유해 ?주|보내 ?주|주실 수 있)",
    r"(필요합니다|필요해요|원합니다|좋을 것 같)",
    r"(제공해 ?주|도와 ?주)",
]
REQUEST_RE = re.compile("|".join(REQUEST_PATTERNS), flags=re.IGNORECASE)


META_QUESTION_PATTERNS = [
    r"(맞죠\??|그렇죠\??|그렇지\??|맞나요\??|아닌가요\??)",
    r"(준비.*(됐|되었)|시작.*(할까요|할까)|끝났|마무리)",
    r"(다 ?됐|거의 다|괜찮|okay\??|right\??)",
]
META_QUESTION_RE = re.compile("|".join(META_QUESTION_PATTERNS), flags=re.IGNORECASE)


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _tokenize_label(label: str) -> List[str]:
    if not label:
        return []
    toks = re.split(r"[\|\^\.:]+", label)
    return [t for t in toks if t]


def _is_noise_text(text: str) -> bool:
    t = re.sub(r"<[^>]+>", " ", text or "").strip()
    if not t:
        return True
    if re.fullmatch(r"[\s,.;:!?-]+", t):
        return True

    # Short fragment (often mistranslated or backchannel), e.g. "엄청난 ."
    toks = [w for w in re.findall(r"[\uac00-\ud7a3A-Za-z0-9]+", t) if w]
    if len(toks) <= 2 and len("".join(toks)) <= 8 and "?" not in t:
        if not ACTION_RE.search(t):
            return True

    # Very short acknowledgement-like
    low = t.lower()
    if len(t.split()) <= 1 and low in {"ok", "okay", "right", "yeah", "yep", "네", "응"}:
        return True
    return False


def _is_meta_question(text: str) -> bool:
    t = re.sub(r"<[^>]+>", " ", text or "").strip()
    if not t:
        return True
    if META_QUESTION_RE.search(t):
        return True
    words = re.findall(r"\w+", t, flags=re.UNICODE)
    if len(words) <= 6 and ("?" in t or t.endswith("요") or t.endswith("죠")):
        return True
    return False


def _has_action_item(text: str, label: str, corpus: str) -> int:
    if ACTION_RE.search(text or ""):
        return 1
    if REQUEST_RE.search(text or ""):
        return 1
    lbl = (label or "").lower()
    if corpus == "ami" and lbl in {"sug", "el.sug"}:
        return 1
    return 0


def _summary_worthy(
    text: str,
    label: str,
    corpus: str,
    utt_id: str,
    extractive_ids: Set[str],
) -> int:
    lbl = (label or "").lower()
    toks = _tokenize_label(lbl)

    # Hard negatives first
    if _is_noise_text(text):
        return 0
    if corpus == "icsi" and toks:
        root0 = toks[0]
        subtags0 = set(toks[1:])
        if root0 == "s" and subtags0.intersection(ICSI_NON_KEY_SUBTAGS):
            return 0

    # Requests/needs are typically summary-worthy even if source dialogue-act is weak.
    if REQUEST_RE.search(text or ""):
        return 1

    # High-confidence positives from extractive IDs (after hard negatives)
    if utt_id and utt_id in extractive_ids:
        return 1

    if corpus == "ami":
        if lbl in AMI_NON_KEY:
            return 0
        if lbl in AMI_KEY_HINT:
            return 1
        return 0

    # ICSI fallback
    if not toks:
        return 0
    root = toks[0]
    if root in {"qy", "qw", "qh", "qr", "qrr"} and _is_meta_question(text):
        return 0
    if root in ICSI_NON_KEY_PREFIX:
        return 0
    if root in ICSI_KEY_PREFIX:
        return 1
    return 0


def _make_3class(is_key: int, has_action: int) -> int:
    if has_action:
        return LABEL_MAP["ACTION"]
    if is_key:
        return LABEL_MAP["KEY"]
    return LABEL_MAP["OTHER"]


def _find_dialogueacts_files(datasets_root: str) -> List[Tuple[str, str]]:
    files: List[Tuple[str, str]] = []
    candidates = [
        ("ami", os.path.join(datasets_root, "ami-corpus", "dialogueActs_kor_manual", "*.json")),
        ("icsi", os.path.join(datasets_root, "icsi-corpus", "dialogueActs_kor_manual", "*.json")),
    ]
    for corpus, pattern in candidates:
        hit = sorted(glob.glob(pattern))
        if not hit:
            fallback = pattern.replace("dialogueActs_kor_manual", "dialogueActs")
            hit = sorted(glob.glob(fallback))
        for p in hit:
            files.append((corpus, p))
    return files


def _build_extractive_index(datasets_root: str) -> Dict[Tuple[str, str], Set[str]]:
    out: Dict[Tuple[str, str], Set[str]] = {}
    for corpus in ("ami", "icsi"):
        corpus_dir = "ami-corpus" if corpus == "ami" else "icsi-corpus"
        ex_dir = os.path.join(datasets_root, corpus_dir, "extractive")
        if not os.path.isdir(ex_dir):
            continue
        for path in sorted(glob.glob(os.path.join(ex_dir, "*.json"))):
            base = os.path.basename(path)
            data = _load_json(path)
            ids: Set[str] = set()
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        utt_id = item.get("id")
                        if utt_id:
                            ids.add(str(utt_id))
            out[(corpus, base)] = ids
    return out


def generate(datasets_root: str, output_path: str):
    files = _find_dialogueacts_files(datasets_root)
    if not files:
        raise RuntimeError("No dialogueActs files found.")

    extractive_index = _build_extractive_index(datasets_root)
    rows = []
    stats = Counter()

    for corpus, path in files:
        base = os.path.basename(path)
        extractive_ids = extractive_index.get((corpus, base), set())
        data = _load_json(path)
        if not isinstance(data, list):
            continue

        meeting_id = os.path.splitext(base)[0]
        for item in data:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text", ""))
            label = str(item.get("label", ""))
            utt_id = str(item.get("id", ""))
            is_key = _summary_worthy(text, label, corpus, utt_id, extractive_ids)
            has_action = _has_action_item(text, label, corpus)
            y = _make_3class(is_key, has_action)
            rows.append(
                {
                    "corpus": corpus,
                    "meeting_id": meeting_id,
                    "utt_id": utt_id,
                    "speaker": item.get("speaker", ""),
                    "text": text,
                    "source_dialogue_label": label,
                    "is_summary_worthy": is_key,
                    "has_action_item": has_action,
                    "label": y,
                }
            )
            stats[f"{corpus}_rows"] += 1
            stats[f"{corpus}_key"] += is_key
            stats[f"{corpus}_action"] += has_action
            stats[f"{corpus}_label_{y}"] += 1

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"saved: {output_path}")
    print(f"rows: {len(rows)}")
    for k in sorted(stats.keys()):
        print(f"{k}: {stats[k]}")


def main():
    parser = argparse.ArgumentParser(description="Generate weak labels for summary/action tasks.")
    parser.add_argument("--datasets-root", default="datasets")
    parser.add_argument(
        "--output",
        default="temp/weak_labels_dialogueacts.jsonl",
        help="Output JSONL path",
    )
    args = parser.parse_args()
    generate(args.datasets_root, args.output)


if __name__ == "__main__":
    main()
