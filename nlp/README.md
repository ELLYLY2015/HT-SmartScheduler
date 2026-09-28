# Phase 2 — ML / NLP Foundation

The ML component does **not** replace the deterministic scheduler.

Pipeline:

```text
original user text
      |
      v
light typo normalization
      |
      v
spaCy NER
      |
      v
DUTY / DATE / TIME / DURATION / REMINDER / TIME_WINDOW / RECURRENCE
      |
      v
existing deterministic time resolver + validation
      |
      v
safe scheduling decision
```

## Dataset

The starter dataset contains exactly 1,000 examples:

```text
800 train
100 validation
100 test
```

The splits use different sentence templates to reduce trivial template leakage.
Normalized text is also deduplicated across all three splits.

The initial dataset is intentionally synthetic/custom. It lets us build and
test the full ML pipeline before adding public corpora and real user-approved
examples.

Do not treat starter evaluation scores as real-world production accuracy.

## Entity labels

- `DUTY`
- `DATE`
- `TIME`
- `DURATION`
- `REMINDER`
- `TIME_WINDOW`
- `RECURRENCE`

## Rebuild the dataset

From the project root:

```bash
python nlp/build_dataset.py
python nlp/validate_dataset.py
```

## Train

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Then:

```bash
python nlp/train_model.py
```

The model is saved to:

```text
nlp/model/
```

## Evaluate

```bash
python nlp/evaluate_model.py
```

This writes:

```text
nlp/evaluation_metrics.json
```

## Try the ML extractor

```bash
python nlp/ml_extractor.py "call docter tomorow at 3 pm for haf an hour"
```

The program preserves the original sentence, normalizes known scheduling typos,
and predicts scheduling entities.

## Human data review

Before expanding/trusting the data, inspect random labeled examples:

```bash
python nlp/sample_for_review.py
```

## Next data milestone

After this starter pipeline works:

1. manually review labels;
2. add public task-oriented/time-expression datasets;
3. add real user-approved examples;
4. expand to 2,000–5,000 examples;
5. add harder paraphrases and typos;
6. calibrate confidence;
7. compare ML extraction against the current rule parser.
