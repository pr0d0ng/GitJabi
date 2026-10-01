import argparse
import json
import os

import numpy as np
import torch
from sklearn.metrics import accuracy_score, f1_score, precision_recall_fscore_support
from sklearn.model_selection import GroupShuffleSplit
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from train_summary_worthy import load_jsonl


def parse_args():
    parser = argparse.ArgumentParser(description="Tune decision threshold on validation split.")
    parser.add_argument(
        "--data-path",
        default="temp/weak_labels_dialogueacts_relabel_v2.jsonl",
        help="JSONL dataset path.",
    )
    parser.add_argument(
        "--model-dir",
        default="outputs/summary_worthy/best_model",
        help="Directory with fine-tuned model/tokenizer.",
    )
    parser.add_argument(
        "--train-config",
        default="outputs/summary_worthy/train_config.json",
        help="Train config json used to reproduce split.",
    )
    parser.add_argument("--label-field", default="is_summary_worthy")
    parser.add_argument("--text-field", default="text")
    parser.add_argument("--group-field", default="meeting_id")
    parser.add_argument("--val-ratio", type=float, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max-length", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--min-threshold", type=float, default=0.05)
    parser.add_argument("--max-threshold", type=float, default=0.95)
    parser.add_argument("--step", type=float, default=0.01)
    parser.add_argument(
        "--metric",
        default="f1",
        choices=["f1", "macro_f1", "accuracy", "precision", "recall"],
        help="Primary metric to pick the best threshold.",
    )
    parser.add_argument(
        "--output-json",
        default="outputs/summary_worthy/threshold_tuning.json",
        help="Where to save summary json.",
    )
    return parser.parse_args()


def load_train_config(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def split_by_group(n_items, labels, groups, val_ratio, seed):
    idx = np.arange(n_items)
    splitter = GroupShuffleSplit(n_splits=1, test_size=val_ratio, random_state=seed)
    _, val_idx = next(splitter.split(idx, labels, groups=groups))
    return val_idx.tolist()


def batched_probs(texts, tokenizer, model, max_length, batch_size):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    model.eval()
    probs = []
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
            probs.extend(p.detach().cpu().numpy().tolist())
    return np.array(probs, dtype=np.float32)


def metrics_at_threshold(y_true, probs, t):
    y_pred = (probs >= t).astype(np.int64)
    p, r, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0
    )
    return {
        "threshold": round(float(t), 4),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(p),
        "recall": float(r),
        "f1": float(f1),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "positive_rate": float(np.mean(y_pred)),
    }


def main():
    args = parse_args()
    cfg = load_train_config(args.train_config)

    val_ratio = args.val_ratio if args.val_ratio is not None else float(cfg.get("val_ratio", 0.1))
    seed = args.seed if args.seed is not None else int(cfg.get("seed", 42))
    max_length = args.max_length if args.max_length is not None else int(cfg.get("max_length", 256))
    text_field = args.text_field or cfg.get("text_field", "text")
    label_field = args.label_field or cfg.get("label_field", "is_summary_worthy")
    group_field = args.group_field or cfg.get("group_field", "meeting_id")

    texts, labels, groups = load_jsonl(
        args.data_path,
        text_field=text_field,
        label_field=label_field,
        group_field=group_field,
        max_samples=0,
    )
    val_idx = split_by_group(len(texts), labels, groups, val_ratio, seed)
    val_texts = [texts[i] for i in val_idx]
    val_labels = np.array([labels[i] for i in val_idx], dtype=np.int64)

    tokenizer = AutoTokenizer.from_pretrained(args.model_dir)
    model = AutoModelForSequenceClassification.from_pretrained(args.model_dir)
    probs = batched_probs(val_texts, tokenizer, model, max_length=max_length, batch_size=args.batch_size)

    thresholds = np.arange(args.min_threshold, args.max_threshold + 1e-8, args.step)
    rows = [metrics_at_threshold(val_labels, probs, float(t)) for t in thresholds]

    best = max(rows, key=lambda x: (x[args.metric], x["f1"], -abs(x["threshold"] - 0.5)))
    near_default = min(rows, key=lambda x: abs(x["threshold"] - 0.5))

    print(f"metric={args.metric}")
    print(
        "best:"
        f" t={best['threshold']:.2f}"
        f" acc={best['accuracy']:.4f}"
        f" p={best['precision']:.4f}"
        f" r={best['recall']:.4f}"
        f" f1={best['f1']:.4f}"
        f" macro_f1={best['macro_f1']:.4f}"
        f" pos_rate={best['positive_rate']:.4f}"
    )
    print(
        "t=0.50:"
        f" t={near_default['threshold']:.2f}"
        f" acc={near_default['accuracy']:.4f}"
        f" p={near_default['precision']:.4f}"
        f" r={near_default['recall']:.4f}"
        f" f1={near_default['f1']:.4f}"
        f" macro_f1={near_default['macro_f1']:.4f}"
        f" pos_rate={near_default['positive_rate']:.4f}"
    )

    os.makedirs(os.path.dirname(args.output_json), exist_ok=True)
    payload = {
        "model_dir": args.model_dir,
        "data_path": args.data_path,
        "label_field": label_field,
        "split": {"val_ratio": val_ratio, "seed": seed, "group_field": group_field},
        "metric": args.metric,
        "best": best,
        "default_0_50": near_default,
        "rows": rows,
    }
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"saved: {args.output_json}")


if __name__ == "__main__":
    main()

