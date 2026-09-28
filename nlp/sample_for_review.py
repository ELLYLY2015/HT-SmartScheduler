from __future__ import annotations

import json
import random
from pathlib import Path


HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"


def main(count: int = 30, seed: int = 20260916):
    records = json.loads(
        (DATA_DIR / "train.json").read_text(encoding="utf-8")
    )

    rng = random.Random(seed)
    sample = rng.sample(records, min(count, len(records)))

    for record in sample:
        print("=" * 80)
        print(record["id"])
        print("ORIGINAL:", record["original_text"])
        print("TRAINING:", record["text"])
        for entity in record["entities"]:
            print(
                f"  {entity['label']:<12} -> {entity['text']!r} "
                f"[{entity['start']}:{entity['end']}]"
            )


if __name__ == "__main__":
    main()
