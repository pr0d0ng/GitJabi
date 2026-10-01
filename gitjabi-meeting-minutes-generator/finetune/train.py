# train.py
import numpy as np
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments,
    set_seed
)
from sklearn.metrics import classification_report
from config import *
from dataset import MeetingDataset
import json

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)

    return {
        "macro_f1": (classification_report(
            labels, preds, output_dict=True
        )["macro avg"]["f1-score"])
    }

def load_jsonl(path):
    texts, labels = [], []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            texts.append(obj["text"])
            labels.append(obj["label"])
    return texts, labels


def main():
    set_seed(SEED)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=NUM_LABELS
    )

    # TODO: 여기서 데이터 연결
    train_texts = [
        "금요일까지 설계를 확정해야 합니다.",
        "이 부분은 지난번에 논의했던 내용입니다."
    ]
    train_labels = [2, 0]  # 예시

    val_texts = [
        "다음 회의에서 다시 확인하겠습니다."
    ]
    val_labels = [1]

    train_dataset = MeetingDataset(
        train_texts, train_labels, tokenizer, MAX_LENGTH
    )
    val_dataset = MeetingDataset(
        val_texts, val_labels, tokenizer, MAX_LENGTH
    )

    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=LEARNING_RATE,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=EVAL_BATCH_SIZE,
        num_train_epochs=EPOCHS,
        weight_decay=WEIGHT_DECAY,
        logging_steps=50,
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        report_to="none"
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics
    )

    trainer.train()
    trainer.save_model(f"{OUTPUT_DIR}/best_model")

if __name__ == "__main__":
    main()
