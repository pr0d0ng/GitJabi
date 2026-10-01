import argparse
import json
import os
import re
from typing import Dict, Iterable, Tuple


AMI_NON_KEY = {"ass", "bck", "stl", "fra", "und", "el.ass", "oth"}

ACTION_RE = re.compile(
    "|".join(
        [
            r"\b(action item|todo|to-do)\b",
            r"\b(should|must|need to|needs to|have to|has to)\b",
            r"\b(let's|let us)\b",
            r"\b(i will|i'll|we will|we'll)\b",
            r"\b(please)\b",
            r"\b(by (monday|tuesday|wednesday|thursday|friday|tomorrow|next week))\b",
            r"(해야|하겠습니다|하자|해요|해 주세요|해주세요|부탁|담당|까지|다음 회의 전|액션 아이템|할 일)",
            r"(겠습니다|할게요|해둘게요|넣을게요|정리할게요|보낼게요|올릴게요|공유할게요|포함시키겠습니다)",
        ]
    ),
    flags=re.IGNORECASE,
)

REQUEST_RE = re.compile(
    "|".join(
        [
            r"(받을 수 있|\bcan i get\b|\bcould i get\b)",
            r"(공유해 ?주|보내 ?주|주실 수 있)",
            r"(필요합니다|필요해요|원합니다|좋을 것 같)",
            r"(제공해 ?주|도와 ?주)",
        ]
    ),
    flags=re.IGNORECASE,
)

DECISION_RE = re.compile(
    "|".join(
        [
            r"(결론|정리하면|결정|합의|확정|요구사항|제약|우선순위|리스크|문제점|다음 단계)",
            r"(정리하자|결정하자|합의하자|확정하자)",
        ]
    ),
    flags=re.IGNORECASE,
)

SHORT_ACK = {"ok", "okay", "right", "yeah", "yep", "네", "응", "좋아요", "맞아요"}


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def _word_tokens(text: str):
    return re.findall(r"[\uac00-\ud7a3A-Za-z0-9]+", text)


def _is_noise(text: str) -> bool:
    t = _strip_tags(text)
    if not t:
        return True
    if re.fullmatch(r"[\s,.;:!?-]+", t):
        return True
    toks = _word_tokens(t)
    if len(toks) <= 2 and len("".join(toks)) <= 8 and "?" not in t and not ACTION_RE.search(t):
        return True
    if len(t.split()) <= 1 and t.lower() in {x.lower() for x in SHORT_ACK}:
        return True
    return False


def relabel_row(row: Dict) -> Tuple[int, int, int]:
    text = row.get("text", "") or ""
    corpus = (row.get("corpus", "") or "").lower()
    src_label = (row.get("source_dialogue_label", "") or "").lower()

    has_action = 1 if (ACTION_RE.search(text) or REQUEST_RE.search(text)) else 0

    if _is_noise(text):
        is_key = 0
    elif has_action:
        is_key = 1
    elif DECISION_RE.search(text):
        is_key = 1
    elif corpus == "ami" and src_label in AMI_NON_KEY:
        is_key = 0
    else:
        # keep previous weak key signal if not confidently overridden
        is_key = 1 if int(row.get("is_summary_worthy", 0)) == 1 else 0

    label = 2 if has_action else (1 if is_key else 0)
    return is_key, has_action, label


def _iter_jsonl(path: str) -> Iterable[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def run(input_path: str, output_path: str, chunk_size: int = 50000):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    total = 0
    changed = 0
    with open(output_path, "w", encoding="utf-8") as out:
        for row in _iter_jsonl(input_path):
            total += 1
            old = (
                int(row.get("is_summary_worthy", 0)),
                int(row.get("has_action_item", 0)),
                int(row.get("label", 0)),
            )
            new = relabel_row(row)
            if old != new:
                changed += 1
            row["is_summary_worthy"] = new[0]
            row["has_action_item"] = new[1]
            row["label"] = new[2]
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            if total % chunk_size == 0:
                print(f"processed: {total} changed: {changed}")
    print(f"done. total={total} changed={changed} output={output_path}")


def main():
    parser = argparse.ArgumentParser(description="Relabel weak labels with stricter heuristics.")
    parser.add_argument("--input", required=True, help="Input JSONL path")
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument("--chunk-size", type=int, default=50000)
    args = parser.parse_args()
    run(args.input, args.output, chunk_size=args.chunk_size)


if __name__ == "__main__":
    main()
