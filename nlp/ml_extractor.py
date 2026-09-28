from __future__ import annotations

import json
import sys
from pathlib import Path

import spacy

try:
    from .normalizer import normalize_text
except ImportError:
    from normalizer import normalize_text


HERE = Path(__file__).resolve().parent
MODEL_DIR = HERE / "model"


class SchedulerMLExtractor:
    def __init__(self, model_path: str | Path = MODEL_DIR):
        model_path = Path(model_path)

        if not model_path.exists():
            raise FileNotFoundError(
                f"ML model not found at {model_path}. "
                "Run python nlp/train_model.py first."
            )

        self.nlp = spacy.load(model_path)

    def analyze(self, text: str) -> dict:
        original = text
        normalized = normalize_text(text)
        doc = self.nlp(normalized)

        return {
            "original_text": original,
            "normalized_text": normalized,
            "entities": [
                {
                    "text": ent.text,
                    "label": ent.label_,
                    "start": ent.start_char,
                    "end": ent.end_char,
                }
                for ent in doc.ents
            ],


            "confidence": {
                "status": "not_calibrated",
                "note": (
                    "Use evaluation metrics plus deterministic validation. "
                    "Entity-level confidence calibration is a later Phase 2 task."
                ),
            },
        }


def main():
    if len(sys.argv) < 2:
        raise SystemExit(
            'Usage: python nlp/ml_extractor.py '
            '"docter tomorow at 3 pm"'
        )

    text = " ".join(sys.argv[1:])
    extractor = SchedulerMLExtractor()
    print(
        json.dumps(
            extractor.analyze(text),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
