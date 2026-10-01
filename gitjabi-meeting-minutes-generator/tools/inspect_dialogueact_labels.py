import argparse
import glob
import json
import os
from collections import Counter, defaultdict


def collect_labels(dialogueacts_dir):
    files = sorted(glob.glob(os.path.join(dialogueacts_dir, "*.json")))
    label_counts = Counter()
    label_examples = defaultdict(set)
    missing_label = 0
    bad_item = 0
    total_items = 0

    for path in files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        if not isinstance(data, list):
            continue

        fname = os.path.basename(path)
        for item in data:
            total_items += 1
            if not isinstance(item, dict):
                bad_item += 1
                continue
            label = item.get("label")
            if label is None or (isinstance(label, str) and label.strip() == ""):
                missing_label += 1
                continue
            if not isinstance(label, str):
                label = str(label)
            label_counts[label] += 1
            if len(label_examples[label]) < 3:
                label_examples[label].add(fname)

    return {
        "files": len(files),
        "total_items": total_items,
        "missing_label_items": missing_label,
        "non_object_items": bad_item,
        "label_counts": label_counts,
        "label_examples": {k: sorted(v) for k, v in label_examples.items()},
    }


def print_report(corpus_name, result):
    print(f"## {corpus_name}")
    print(f"files: {result['files']}")
    print(f"items: {result['total_items']}")
    print(f"missing_label_items: {result['missing_label_items']}")
    print(f"non_object_items: {result['non_object_items']}")
    print(f"unique_labels: {len(result['label_counts'])}")
    print("labels:")
    for label, count in result["label_counts"].most_common():
        examples = ", ".join(result["label_examples"].get(label, []))
        print(f"  - {label}: {count} [{examples}]")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Inspect possible label values in AMI/ICSI dialogueActs datasets."
    )
    parser.add_argument(
        "--datasets-root",
        default="datasets",
        help="Root directory that contains ami-corpus and icsi-corpus.",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Optional path to save machine-readable summary JSON.",
    )
    args = parser.parse_args()

    corpora = {
        "ami-corpus": os.path.join(args.datasets_root, "ami-corpus", "dialogueActs"),
        "icsi-corpus": os.path.join(args.datasets_root, "icsi-corpus", "dialogueActs"),
    }

    summary = {}
    for name, path in corpora.items():
        if not os.path.isdir(path):
            print(f"skip {name}: not found ({path})")
            continue
        result = collect_labels(path)
        summary[name] = {
            "files": result["files"],
            "total_items": result["total_items"],
            "missing_label_items": result["missing_label_items"],
            "non_object_items": result["non_object_items"],
            "unique_labels": len(result["label_counts"]),
            "label_counts": dict(result["label_counts"]),
            "label_examples": result["label_examples"],
        }
        print_report(name, result)

    if args.output_json:
        out_dir = os.path.dirname(args.output_json)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"saved: {args.output_json}")


if __name__ == "__main__":
    main()
