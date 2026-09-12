"""Deciding whether two values agree.

This is where `unverifiable` earns its place. The rule throughout: a difference
the system cannot confidently explain is handed to the officer, never resolved
by guessing. "Rajesh Kumar" against "Rajesh Kumaar" is not a mismatch and not a
match — it is a judgement about whether a transliteration differs or a person
does, and that judgement belongs to a human.

Deterministic, and independent of any model. A check can consult a model for a
harder reading, but the comparison itself is code you can read and test.
"""

import re
import unicodedata
from datetime import date
from typing import Literal

Verdict = Literal["verified", "mismatch", "unverifiable"]

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d")


def _fold(value: str) -> str:
    """Casefold, strip accents and collapse whitespace and punctuation."""
    decomposed = unicodedata.normalize("NFKD", value)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", stripped.casefold()).strip()


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb))
            )
        previous = current
    return previous[-1]


def parse_date(value: str) -> date | None:
    from datetime import datetime

    text = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def compare_date(document: str, reference: str) -> tuple[Verdict, float]:
    left, right = parse_date(document), parse_date(reference)
    if left is None or right is None:
        # An unparseable date is not a mismatch — we do not know what it says.
        return "unverifiable", 0.3
    if left == right:
        return "verified", 0.99
    # Day and month transposed is the classic data-entry error, and it is not
    # the system's place to decide which of the two is right.
    if left.year == right.year and left.day == right.month and left.month == right.day:
        return "unverifiable", 0.5
    return "mismatch", 0.97


def compare_name(document: str, reference: str) -> tuple[Verdict, float]:
    left, right = _fold(document), _fold(reference)
    if not left or not right:
        return "unverifiable", 0.2
    if left == right:
        return "verified", 0.99

    # Same words in a different order: "Kumar Rajesh" vs "Rajesh Kumar".
    if sorted(left.split()) == sorted(right.split()):
        return "verified", 0.9

    distance = _levenshtein(left, right)
    longest = max(len(left), len(right))
    similarity = 1 - distance / longest

    # Close but not identical: a transliteration variant and a different person
    # look the same from here. Hand it over.
    if similarity >= 0.75:
        return "unverifiable", round(similarity, 2)

    # An initial standing in for a full name, either direction.
    left_parts, right_parts = left.split(), right.split()
    if left_parts and right_parts and left_parts[-1] == right_parts[-1]:
        if any(len(p) == 1 for p in left_parts + right_parts):
            return "unverifiable", 0.5

    return "mismatch", round(1 - similarity, 2)


def compare_amount(document: str, reference: str) -> tuple[Verdict, float]:
    def to_number(value: str) -> int | None:
        digits = re.sub(r"[^0-9]", "", value)
        return int(digits) if digits else None

    left, right = to_number(document), to_number(reference)
    if left is None or right is None:
        return "unverifiable", 0.2
    if left == right:
        return "verified", 0.99
    return "mismatch", 0.95


def compare_text(document: str, reference: str) -> tuple[Verdict, float]:
    left, right = _fold(document), _fold(reference)
    if not left or not right:
        return "unverifiable", 0.2
    if left == right:
        return "verified", 0.99
    if left in right or right in left:
        return "unverifiable", 0.6
    return "mismatch", 0.8


#: Which comparison a field gets. An unlisted field falls back to text.
COMPARATORS = {
    "date_of_birth": compare_date,
    "issued_on": compare_date,
    "full_name": compare_name,
    "father_name": compare_name,
    "annual_income": compare_amount,
}


def compare(field: str, document: str, reference: str) -> tuple[Verdict, float]:
    return COMPARATORS.get(field, compare_text)(document, reference)
