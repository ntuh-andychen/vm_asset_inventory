from __future__ import annotations

from typing import Iterable


def join_unique(values: Iterable[str], delimiter: str = ":") -> str:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        v = (value or "").strip()
        if not v or v in seen:
            continue
        seen.add(v)
        out.append(v)
    return delimiter.join(out)


def to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
