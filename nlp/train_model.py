from __future__ import annotations

import json
import random
from pathlib import Path

import spacy
from spacy.training import Example
from spacy.util import minibatch, compounding


HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
MODEL_DIR = HERE / "model"

LABELS = [
    "DUTY",
    "DATE",
    "TIME",
    "DURATION",
    "REMINDER",
    "TIME_WINDOW",
    "RECURRENCE",
]


def load_examples(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def to_spacy_examples(nlp, records):
    examples = []

    for record in records:
        doc = nlp.make_doc(record["text"])
        entities = [
            (entity["start"], entity["end"], entity["label"])
            for entity in record["entities"]
        ]
        examples.append(
            Example.from_dict(
                doc,
                {"entities": entities},
            )
        )

    return examples


def train(
    epochs: int = 6,
    dropout: float = 0.20,
    seed: int = 20260916,
):
    random.seed(seed)
    spacy.util.fix_random_seed(seed)

    train_records = load_examples(DATA_DIR / "train.json")
    validation_records = load_examples(DATA_DIR / "validation.json")

    nlp = spacy.blank("en")
    ner = nlp.add_pipe("ner")

    for label in LABELS:
        ner.add_label(label)

    train_examples = to_spacy_examples(nlp, train_records)
    validation_examples = to_spacy_examples(nlp, validation_records)

    optimizer = nlp.initialize(get_examples=lambda: train_examples)

    best_score = -1.0
    best_bytes = None
    history = []

    for epoch in range(1, epochs + 1):
        random.shuffle(train_examples)
        losses = {}

        batches = minibatch(
            train_examples,
            size=compounding(8.0, 32.0, 1.001),
        )

        for batch in batches:
            nlp.update(
                batch,
                drop=dropout,
                sgd=optimizer,
                losses=losses,
            )

        scores = nlp.evaluate(validation_examples)
        f1 = float(scores.get("ents_f", 0.0))

        history.append(
            {
                "epoch": epoch,
                "loss_ner": round(float(losses.get("ner", 0.0)), 4),
                "validation_precision": round(
                    float(scores.get("ents_p", 0.0)), 4
                ),
                "validation_recall": round(
                    float(scores.get("ents_r", 0.0)), 4
                ),
                "validation_f1": round(f1, 4),
            }
        )

        print(
            f"Epoch {epoch:02d} "
            f"loss={losses.get('ner', 0.0):.3f} "
            f"val_f1={f1:.3f}"
        )

        if f1 > best_score:
            best_score = f1
            best_bytes = nlp.to_bytes()

    if best_bytes is not None:
        nlp.from_bytes(best_bytes)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    nlp.to_disk(MODEL_DIR)

    summary = {
        "epochs": epochs,
        "dropout": dropout,
        "seed": seed,
        "best_validation_f1": round(best_score, 4),
        "history": history,
        "note": (
            "Metrics are on a synthetic/custom starter dataset. "
            "They do not represent real-world production accuracy."
        ),
    }

    (HERE / "training_metrics.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print(f"\nModel saved to: {MODEL_DIR}")
    print(f"Best validation F1: {best_score:.4f}")


if __name__ == "__main__":
    train()
