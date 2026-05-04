import re
from typing import Optional

MAX_SCORE = 100
MIN_SCORE = 0


def clamp_score(value: int) -> int:
    return max(MIN_SCORE, min(MAX_SCORE, value))


def normalize_text(value: Optional[str]) -> str:
    return re.sub(r"\s+", "", value or "").lower()


def token_overlap_count(left: str, right: str) -> int:
    left_tokens = {normalize_text(token) for token in re.split(r"[\s,;/|]+", left or "") if normalize_text(token)}
    right_text = normalize_text(right)
    return sum(1 for token in left_tokens if token and token in right_text)


def parse_int(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def contains_any(*values: Optional[str], keywords: list[str]) -> bool:
    text = " ".join(value or "" for value in values)
    return any(keyword.lower() in text.lower() for keyword in keywords)
