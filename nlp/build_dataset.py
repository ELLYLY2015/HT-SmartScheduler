from __future__ import annotations

import json
import random
import re
from pathlib import Path

from normalizer import normalize_text


HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"

LABELS = {
    "DUTY",
    "DATE",
    "TIME",
    "DURATION",
    "REMINDER",
    "TIME_WINDOW",
    "RECURRENCE",
}

DUTIES = [


    "dentist",
    "doctor appointment",
    "meeting",
    "team meeting",
    "therapy",
    "physical therapy",
    "medicine",
    "class",
    "lunch",
    "dinner",
    "work",
    "appointment",
    "call mom",
    "call the doctor",
    "see my dentist",
    "go to the dentist",
    "attend the team meeting",
    "meet Sarah",
    "meet John",
    "study for biology",
    "study for the exam",
    "finish the project",
    "submit the report",
    "send the client email",
    "pick up groceries",
    "take medicine",
    "start laundry",
    "check the oven",
    "pay the electricity bill",
    "renew my insurance",
    "work on the presentation",
    "go to the gym",
    "practice piano",
    "review the budget",
    "join the Zoom meeting",
    "take the car for service",
    "pick up the prescription",
    "finish homework",
    "prepare dinner",
    "walk the dog",
    "call the bank",
    "book a haircut",
    "attend class",
    "visit my parents",
    "file the expense report",
    "prepare for the interview",
    "write the proposal",
    "check in with my manager",
    "drop off the package",
    "return the library books",
    "water the plants",
    "take a break",
]

DATES = [
    "tomorrow",
    "the day after tomorrow",
    "next Monday",
    "next Tuesday",
    "next Wednesday",
    "next Thursday",
    "next Friday",
    "this Saturday",
    "this Sunday",
    "September 20",
    "September 25",
    "October 2",
    "10/05/2026",
    "2026-10-12",
]

TIMES = [
    "7 am",
    "8:30 am",
    "9 am",
    "10:15 am",
    "11 am",
    "12 pm",
    "1:30 pm",
    "2 pm",
    "3 pm",
    "4:45 pm",
    "6 pm",
    "7:30 pm",
    "8 pm",
    "morning",
    "afternoon",
    "evening",
    "noon",
]

AMBIGUOUS_TIMES = ["2", "3", "7", "10", "11"]

DURATIONS = [
    "15 minutes",
    "20 minutes",
    "30 minutes",
    "45 minutes",
    "half an hour",
    "one hour",
    "90 minutes",
    "two hours",
    "three hours",
]

REMINDERS = [
    "5 minutes before",
    "10 minutes before",
    "15 minutes before",
    "30 minutes before",
    "45 minutes before",
    "one hour before",
    "two hours before",
    "one day before",
]

def _relative_exact_phrases() -> list[str]:
    """Build broad exact-relative examples for the app's scheduling convention.

    In Smart Scheduler, quantified phrases such as "in the next 15 minutes"
    and "within the next 2 hours" mean current local time + the quantity.
    Truly vague phrases such as "sometime next week" remain TIME_WINDOW.
    """
    units = {
        "minute": [5, 10, 15, 20, 30, 45],
        "hour": [1, 2, 3, 4, 6, 12],
        "day": [1, 2, 3, 5, 7],
        "week": [1, 2, 3, 4],
        "month": [1, 2, 3, 6, 12],
    }
    phrases: list[str] = []
    for unit, values in units.items():
        for value in values:
            noun = unit if value == 1 else unit + "s"
            phrases.extend([
                f"in {value} {noun}",
                f"in the next {value} {noun}",
                f"in next {value} {noun}",
                f"within {value} {noun}",
                f"within the next {value} {noun}",
                f"{value} {noun} from now",
                f"after {value} {noun}",
            ])

    phrases.extend([
        "in half an hour",
        "in half hour",
        "half an hour from now",
        "in a quarter hour",
        "in an hour",
        "one hour from now",
        "in two hours",
        "two hours from now",
        "in two days",
        "three days from now",
        "in two weeks",
        "in one month",
    ])

    return list(dict.fromkeys(phrases))


RELATIVE_EXACT = _relative_exact_phrases()

WINDOWS = [
    "sometime later today",
    "sometime tomorrow",
    "sometime next week",
    "sometime this weekend",
    "sometime next month",
    "before the end of the week",
    "before the end of the month",
    "by next week",
    "by next month",
    "later this week",
    "later this month",
]

RECURRENCES = [
    "every day",
    "daily",
    "every Monday",
    "every Tuesday",
    "every Wednesday",
    "every Thursday",
    "every Friday",
    "every weekend",
    "each weekday",
    "every other day",
    "once a week",
]

TYPO_MAP = {
    "tomorrow": "tomorow",
    "next": "nxt",
    "meeting": "metting",
    "doctor": "docter",
    "dentist": "dentst",
    "medicine": "medcine",
    "half": "haf",
    "hour": "hr",
    "hours": "hrs",
    "minutes": "mins",
    "from": "frm",
    "Friday": "Frday",
    "morning": "mornin",
    "afternoon": "afternon",
    "evening": "evning",
}


TRAIN_TEMPLATES = {
    "exact": [
        "{DUTY} {DATE} at {TIME}",
        "I need to {DUTY} {DATE} at {TIME}",
        "Please schedule {DUTY} for {DATE} at {TIME}",
        "{DATE} at {TIME} I need to {DUTY}",
        "Put {DUTY} on my schedule {DATE} at {TIME}",
        "Don't let me forget to {DUTY} {DATE} at {TIME}",
    ],
    "duration_reminder": [
        "{DUTY} {DATE} at {TIME} for {DURATION} remind me {REMINDER}",
        "Schedule {DUTY} for {DATE} at {TIME}, it lasts {DURATION}, reminder {REMINDER}",
        "I have to {DUTY} {DATE} at {TIME} for {DURATION}; alert me {REMINDER}",
        "{DATE} {TIME}: {DUTY} for {DURATION}, remind me {REMINDER}",
    ],
    "relative": [
        "{DUTY} {DATE}",
        "I need to {DUTY} {DATE}",
        "Remind me to {DUTY} {DATE}",
        "{DATE}, {DUTY}",
    ],
    "relative_duration": [
        "{DUTY} {DATE} lasting {DURATION}",
        "{DUTY} today {DATE} lasting {DURATION}",
        "{DUTY} {DATE} for {DURATION}",
        "I have {DUTY} {DATE}; it lasts {DURATION}",
        "Schedule {DUTY} {DATE}, duration {DURATION}",
        "{DUTY} today {DATE} for {DURATION}",
    ],
    "recurrence": [
        "{DUTY} {RECURRENCE} at {TIME}",
        "Schedule {DUTY} {RECURRENCE} at {TIME}",
        "I want to {DUTY} {RECURRENCE} at {TIME}",
    ],
    "window": [
        "{DUTY} {TIME_WINDOW}",
        "I need to {DUTY} {TIME_WINDOW}",
        "Try to fit in {DUTY} {TIME_WINDOW}",
    ],
    "ambiguous": [
        "{DUTY} at {TIME}",
        "{DUTY} {DATE}",
        "I need to {DUTY} at {TIME}",
    ],
}

VALIDATION_TEMPLATES = {
    "exact": [
        "Can you add {DUTY} {DATE} around {TIME}",
        "My schedule needs {DUTY} on {DATE} at {TIME}",
    ],
    "duration_reminder": [
        "Add {DUTY} {DATE} at {TIME}; block {DURATION} and notify me {REMINDER}",
        "Set up {DUTY} for {DATE} {TIME}, duration {DURATION}, warning {REMINDER}",
    ],
    "relative": [
        "Make sure I {DUTY} {DATE}",
        "I should {DUTY} {DATE}",
    ],
    "relative_duration": [
        "Add {DUTY} {DATE} lasting {DURATION}",
        "I have {DUTY} today {DATE}; block {DURATION}",
        "Put {DUTY} {DATE} on my schedule for {DURATION}",
    ],
    "recurrence": [
        "Keep {DUTY} on the calendar {RECURRENCE} at {TIME}",
    ],
    "window": [
        "Find time to {DUTY} {TIME_WINDOW}",
    ],
    "ambiguous": [
        "Put down {DUTY} at {TIME}",
        "Remember {DUTY} {DATE}",
    ],
}

TEST_TEMPLATES = {
    "exact": [
        "Add this for me: {DUTY}, {DATE}, {TIME}",
        "I've got to {DUTY} {DATE} at about {TIME}",
    ],
    "duration_reminder": [
        "Calendar {DUTY} {DATE} {TIME} for {DURATION}; give me a heads-up {REMINDER}",
        "Book {DUTY} on {DATE} at {TIME}, reserve {DURATION}, ping me {REMINDER}",
    ],
    "relative": [
        "Put a reminder so I {DUTY} {DATE}",
        "Need to {DUTY} {DATE}",
    ],
    "relative_duration": [
        "Calendar {DUTY} {DATE} lasting {DURATION}",
        "I've got {DUTY} today {DATE} for {DURATION}",
        "Book {DUTY} {DATE}; duration {DURATION}",
    ],
    "recurrence": [
        "Repeat {DUTY} {RECURRENCE} at {TIME}",
    ],
    "window": [
        "Somewhere {TIME_WINDOW}, I need to {DUTY}",
    ],
    "ambiguous": [
        "Add {DUTY} for {TIME}",
        "Don't forget {DUTY} {DATE}",
    ],
}


def render_template(template: str, slots: dict[str, str]) -> tuple[str, list[dict]]:
    """
    Render a template and calculate exact character spans.
    Repeated placeholders are supported.
    """
    parts = []
    entities = []
    cursor = 0
    pattern = re.compile(r"\{([A-Z_]+)\}")

    for match in pattern.finditer(template):
        literal = template[cursor:match.start()]
        parts.append(literal)

        label = match.group(1)
        value = slots[label]
        start = sum(len(part) for part in parts)
        parts.append(value)
        end = start + len(value)

        entities.append(
            {
                "start": start,
                "end": end,
                "label": label,
                "text": value,
            }
        )
        cursor = match.end()

    parts.append(template[cursor:])
    text = "".join(parts)

    return text, entities


def corrupt_text(text: str, rng: random.Random) -> str:
    words = text.split(" ")
    candidates = [
        i for i, word in enumerate(words)
        if re.sub(r"[^A-Za-z]", "", word) in TYPO_MAP
        or re.sub(r"[^A-Za-z]", "", word).lower() in {
            key.lower() for key in TYPO_MAP
        }
    ]

    if not candidates:

        return text.replace(" at ", "  at ", 1)

    rng.shuffle(candidates)
    number = min(len(candidates), rng.choice([1, 1, 2]))

    for index in candidates[:number]:
        raw = words[index]
        prefix = re.match(r"^\W*", raw).group(0)
        suffix = re.search(r"\W*$", raw).group(0)
        core = raw[len(prefix): len(raw) - len(suffix) if suffix else None]

        replacement = None
        for correct, typo in TYPO_MAP.items():
            if core.lower() == correct.lower():
                replacement = typo
                break

        if replacement:
            words[index] = prefix + replacement + suffix

    return " ".join(words)


def make_example(
    split: str,
    category: str,
    rng: random.Random,
    noisy: bool = False,
) -> dict:
    templates = {
        "train": TRAIN_TEMPLATES,
        "validation": VALIDATION_TEMPLATES,
        "test": TEST_TEMPLATES,
    }[split]

    duty = rng.choice(DUTIES)

    slots = {
        "DUTY": duty,
        "DATE": rng.choice(DATES),
        "TIME": rng.choice(TIMES),
        "DURATION": rng.choice(DURATIONS),
        "REMINDER": rng.choice(REMINDERS),
        "TIME_WINDOW": rng.choice(WINDOWS),
        "RECURRENCE": rng.choice(RECURRENCES),
    }

    if category in {"relative", "relative_duration"}:
        slots["DATE"] = rng.choice(RELATIVE_EXACT)

    if category == "ambiguous":
        if rng.random() < 0.55:
            slots["TIME"] = rng.choice(AMBIGUOUS_TIMES)

    template = rng.choice(templates[category])
    normalized_text, entities = render_template(template, slots)

    original_text = (
        corrupt_text(normalized_text, rng)
        if noisy
        else normalized_text
    )



    if noisy:
        normalized_from_original = normalize_text(original_text)
        if normalized_from_original != normalized_text:

            normalized_text = normalized_from_original



            rebuilt = []
            search_from = 0
            for entity in entities:
                value = entity["text"]
                pos = normalized_text.find(value, search_from)
                if pos < 0:


                    corrected_value = normalize_text(value)
                    pos = normalized_text.find(corrected_value, search_from)
                    value = corrected_value
                if pos < 0:
                    raise ValueError(
                        f"Could not rebuild entity '{entity['text']}' "
                        f"in '{normalized_text}'"
                    )
                rebuilt.append(
                    {
                        "start": pos,
                        "end": pos + len(value),
                        "label": entity["label"],
                        "text": value,
                    }
                )
                search_from = pos + len(value)
            entities = rebuilt

    return {
        "original_text": original_text,
        "text": normalized_text,
        "entities": entities,
        "meta": {
            "split": split,
            "category": "noisy" if noisy else category,
            "source": "synthetic_custom",
        },
    }


def make_multi_event(split: str, rng: random.Random) -> dict:

    if split == "train":
        connector = rng.choice([". ", "; ", " and then "])
        first_template = "{DUTY} {DATE} at {TIME}"
        second_template = "{DUTY} {DATE} at {TIME}"
    elif split == "validation":
        connector = " plus "
        first_template = "First {DUTY} {DATE} at {TIME}"
        second_template = "then {DUTY} {DATE} at {TIME}"
    else:
        connector = " after that "
        first_template = "I have {DUTY} {DATE} at {TIME}"
        second_template = "I also need to {DUTY} {DATE} at {TIME}"

    def one(template):
        return render_template(
            template,
            {
                "DUTY": rng.choice(DUTIES),
                "DATE": rng.choice(DATES),
                "TIME": rng.choice(TIMES),
            },
        )

    text1, entities1 = one(first_template)
    text2, entities2 = one(second_template)
    offset = len(text1) + len(connector)

    entities2 = [
        {
            **entity,
            "start": entity["start"] + offset,
            "end": entity["end"] + offset,
        }
        for entity in entities2
    ]

    text = text1 + connector + text2

    return {
        "original_text": text,
        "text": text,
        "entities": entities1 + entities2,
        "meta": {
            "split": split,
            "category": "multi_event",
            "source": "synthetic_custom",
        },
    }


SPLIT_COUNTS = {
    "train": {
        "exact": 300,
        "relative": 220,
        "relative_duration": 220,
        "duration_reminder": 120,
        "recurrence": 70,
        "window": 60,
        "noisy": 60,
        "ambiguous": 30,
        "multi_event": 20,
    },
    "validation": {
        "exact": 40,
        "relative": 30,
        "relative_duration": 30,
        "duration_reminder": 15,
        "recurrence": 10,
        "window": 8,
        "noisy": 5,
        "ambiguous": 5,
        "multi_event": 2,
    },
    "test": {
        "exact": 40,
        "relative": 30,
        "relative_duration": 30,
        "duration_reminder": 15,
        "recurrence": 10,
        "window": 8,
        "noisy": 5,
        "ambiguous": 5,
        "multi_event": 2,
    },
}


def generate_split(
    split: str,
    counts: dict[str, int],
    rng: random.Random,
    global_seen: set[str],
) -> list[dict]:
    examples = []

    for category, target in counts.items():
        made = 0
        attempts = 0

        while made < target:
            attempts += 1
            if attempts > target * 500:
                raise RuntimeError(
                    f"Could not create enough unique {split}/{category} examples."
                )

            if category == "multi_event":
                example = make_multi_event(split, rng)
            elif category == "noisy":

                base_category = rng.choice(
                    ["exact", "relative", "duration_reminder"]
                )
                example = make_example(
                    split,
                    base_category,
                    rng,
                    noisy=True,
                )
            else:
                example = make_example(split, category, rng)

            key = example["text"].lower()

            if key in global_seen:
                continue

            global_seen.add(key)
            examples.append(example)
            made += 1

    rng.shuffle(examples)

    for index, example in enumerate(examples, start=1):
        example["id"] = f"{split}-{index:04d}"

    return examples


def build(seed: int = 20260916):
    rng = random.Random(seed)
    global_seen = set()
    all_splits = {}

    for split in ("train", "validation", "test"):
        examples = generate_split(
            split,
            SPLIT_COUNTS[split],
            rng,
            global_seen,
        )
        all_splits[split] = examples

        path = DATA_DIR / f"{split}.json"
        path.write_text(
            json.dumps(examples, indent=2),
            encoding="utf-8",
        )

    combined = (
        all_splits["train"]
        + all_splits["validation"]
        + all_splits["test"]
    )

    (DATA_DIR / "training_data.json").write_text(
        json.dumps(combined, indent=2),
        encoding="utf-8",
    )

    stats = {
        "seed": seed,
        "total": len(combined),
        "splits": {
            name: len(items)
            for name, items in all_splits.items()
        },
        "categories": {},
        "entity_counts": {label: 0 for label in sorted(LABELS)},
    }

    for example in combined:
        category = example["meta"]["category"]
        stats["categories"][category] = (
            stats["categories"].get(category, 0) + 1
        )

        for entity in example["entities"]:
            stats["entity_counts"][entity["label"]] += 1

    (DATA_DIR / "dataset_stats.json").write_text(
        json.dumps(stats, indent=2),
        encoding="utf-8",
    )

    return stats


if __name__ == "__main__":
    stats = build()
    print(json.dumps(stats, indent=2))
