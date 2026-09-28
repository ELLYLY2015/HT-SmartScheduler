from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"

VALID_LABELS = {
    "DUTY",
    "DATE",
    "TIME",
    "DURATION",
    "REMINDER",
    "TIME_WINDOW",
    "RECURRENCE",
}


def load(name: str):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def validate_file(name: str) -> dict:
    examples = load(name)
    seen_text = set()
    entity_counts = Counter()

    for example in examples:
        text = example["text"]

        if not text.strip():
            raise ValueError(f"{name}: blank text in {example['id']}")

        lower = text.lower()
        if lower in seen_text:
            raise ValueError(
                f"{name}: duplicate normalized text in {example['id']}"
            )
        seen_text.add(lower)

        spans = []

        for entity in example["entities"]:
            label = entity["label"]
            start = entity["start"]
            end = entity["end"]

            if label not in VALID_LABELS:
                raise ValueError(
                    f"{name}: invalid label {label} in {example['id']}"
                )

            if not (0 <= start < end <= len(text)):
                raise ValueError(
                    f"{name}: invalid offsets in {example['id']}: {entity}"
                )

            actual = text[start:end]
            if actual != entity["text"]:
                raise ValueError(
                    f"{name}: span mismatch in {example['id']}: "
                    f"expected {entity['text']!r}, got {actual!r}"
                )

            for old_start, old_end in spans:
                if start < old_end and end > old_start:
                    raise ValueError(
                        f"{name}: overlapping entities in {example['id']}"
                    )

            spans.append((start, end))
            entity_counts[label] += 1

    return {
        "examples": len(examples),
        "entities": dict(sorted(entity_counts.items())),
        "texts": seen_text,
    }


def main():
    results = {}

    for name in ("train.json", "validation.json", "test.json"):
        results[name] = validate_file(name)

    train_texts = results["train.json"]["texts"]
    val_texts = results["validation.json"]["texts"]
    test_texts = results["test.json"]["texts"]

    if train_texts & val_texts:
        raise ValueError("Leakage: train and validation share text.")
    if train_texts & test_texts:
        raise ValueError("Leakage: train and test share text.")
    if val_texts & test_texts:
        raise ValueError("Leakage: validation and test share text.")

    printable = {
        name: {
            "examples": result["examples"],
            "entities": result["entities"],
        }
        for name, result in results.items()
    }

    print("Dataset validation passed.")
    print(json.dumps(printable, indent=2))


if __name__ == "__main__":
    main()
