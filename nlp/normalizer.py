from __future__ import annotations

import re




WORD_CORRECTIONS = {
    "tomorow": "tomorrow",
    "tommorow": "tomorrow",
    "tmrw": "tomorrow",
    "tmr": "tomorrow",
    "nxt": "next",
    "nex": "next",
    "nextt": "next",
    "ths": "this",
    "tis": "this",
    "thsi": "this",
    "metting": "meeting",
    "meetin": "meeting",
    "docter": "doctor",
    "docotr": "doctor",
    "dentst": "dentist",
    "medcine": "medicine",
    "medecine": "medicine",
    "frday": "friday",
    "thurday": "thursday",
    "wednsday": "wednesday",
    "tusday": "tuesday",
    "saterday": "saturday",
    "haf": "half",
    "hrs": "hours",
    "hr": "hour",
    "mins": "minutes",
    "min": "minute",
    "frm": "from",
    "mornin": "morning",
    "afternon": "afternoon",
    "evning": "evening",
    "rember": "remember",
    "remindr": "reminder",
}


def _edit_distance(left: str, right: str) -> int:
    """Small Levenshtein distance helper used only for scheduling keywords."""
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous = list(range(len(right) + 1))
    for i, lch in enumerate(left, start=1):
        current = [i]
        for j, rch in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[j] + 1,
                    previous[j - 1] + (lch != rch),
                )
            )
        previous = current
    return previous[-1]


def _restore_case(raw: str, corrected: str) -> str:
    if raw.isupper():
        return corrected.upper()
    if raw[:1].isupper():
        return corrected.capitalize()
    return corrected


def _normalize_weekend_words(text: str) -> str:

    text = re.sub(r"\bweek\s*[- ]\s*end\b", "weekend", text, flags=re.IGNORECASE)




    def fix_weekend(match: re.Match) -> str:
        raw = match.group(0)
        low = raw.lower()
        if low == "weekend":
            return raw
        if low.startswith("w") and 4 <= len(low) <= 9 and _edit_distance(low, "weekend") <= 2:
            return _restore_case(raw, "weekend")
        return raw

    text = re.sub(r"\b[A-Za-z]+\b", fix_weekend, text)



    def fix_modifier(match: re.Match) -> str:
        raw = match.group(1)
        low = raw.lower()
        if low in {"coming", "upcoming"}:

            return "weekend"
        if low in {"this", "next"}:
            return f"{raw} weekend"
        if _edit_distance(low, "this") <= 1 or low == "thsi":
            return f"{_restore_case(raw, 'this')} weekend"
        if _edit_distance(low, "next") <= 1:
            return f"{_restore_case(raw, 'next')} weekend"
        return match.group(0)

    text = re.sub(r"\b([A-Za-z]+)\s+weekend\b", fix_modifier, text, flags=re.IGNORECASE)


    text = re.sub(r"\bthe\s+weekend\b", "weekend", text, flags=re.IGNORECASE)
    text = re.sub(
        r"\b(?:the\s+)?weekend\s+after\s+(?:the\s+)?next\b",
        "weekend after next",
        text,
        flags=re.IGNORECASE,
    )
    return text


def normalize_text(text: str) -> str:
    """
    Light, conservative cleanup before ML and deterministic parsing.

    - collapses repeated whitespace
    - fixes a small scheduling-specific typo dictionary
    - fuzzily repairs the scheduling keyword "weekend" and nearby this/next
    - preserves punctuation/casing as much as practical

    We intentionally do NOT guess missing AM/PM, dates, or event meaning.
    """
    text = re.sub(r"\s+", " ", text.strip())

    def replace_word(match: re.Match) -> str:
        raw = match.group(0)
        corrected = WORD_CORRECTIONS.get(raw.lower())
        if corrected is None:
            return raw
        return _restore_case(raw, corrected)

    text = re.sub(r"\b[A-Za-z]+\b", replace_word, text)
    return _normalize_weekend_words(text)
