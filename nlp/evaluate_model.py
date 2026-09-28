from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import spacy


HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
MODEL_DIR = HERE / "model"


def entity_set_from_record(record):
    return {
        (entity["start"], entity["end"], entity["label"])
        for entity in record["entities"]
    }


def entity_set_from_doc(doc):
    return {
        (entity.start_char, entity.end_char, entity.label_)
        for entity in doc.ents
    }


def safe_prf(tp: int, fp: int, fn: int):
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return precision, recall, f1


def evaluate():
    if not MODEL_DIR.exists():
        raise SystemExit(
            "Model not found. Run: python nlp/train_model.py"
        )

    nlp = spacy.load(MODEL_DIR)
    records = json.loads(
        (DATA_DIR / "test.json").read_text(encoding="utf-8")
    )

    overall = Counter()
    per_label = {}

    labels = [
        "DUTY",
        "DATE",
        "TIME",
        "DURATION",
        "REMINDER",
        "TIME_WINDOW",
        "RECURRENCE",
    ]

    for label in labels:
        per_label[label] = Counter()

    exact_sentence_matches = 0

    for record in records:
        gold = entity_set_from_record(record)
        pred = entity_set_from_doc(nlp(record["text"]))

        if gold == pred:
            exact_sentence_matches += 1

        for item in pred & gold:
            overall["tp"] += 1
            per_label[item[2]]["tp"] += 1

        for item in pred - gold:
            overall["fp"] += 1
            per_label[item[2]]["fp"] += 1

        for item in gold - pred:
            overall["fn"] += 1
            per_label[item[2]]["fn"] += 1

    p, r, f1 = safe_prf(
        overall["tp"],
        overall["fp"],
        overall["fn"],
    )

    result = {
        "test_examples": len(records),
        "exact_sentence_entity_match": round(
            exact_sentence_matches / len(records),
            4,
        ),
        "overall": {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f1, 4),
            "tp": overall["tp"],
            "fp": overall["fp"],
            "fn": overall["fn"],
        },
        "per_label": {},
        "warning": (
            "This is a starter synthetic/custom benchmark. "
            "Real user text will be harder."
        ),
    }

    for label in labels:
        counts = per_label[label]
        lp, lr, lf1 = safe_prf(
            counts["tp"],
            counts["fp"],
            counts["fn"],
        )
        result["per_label"][label] = {
            "precision": round(lp, 4),
            "recall": round(lr, 4),
            "f1": round(lf1, 4),
            "support": counts["tp"] + counts["fn"],
        }

    (HERE / "evaluation_metrics.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    evaluate()
