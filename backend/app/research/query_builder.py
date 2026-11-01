from __future__ import annotations

import re

NOISE_PATTERNS = [
    r"\blot\s*\d+\b",
    r"\bas is\b",
    r"\bsee pics?\b",
    r"\bno reserve\b",
    r"\bassorted\b",
]

BULK_MARKERS = ["box of", "lot of", "assorted", "mixed lot"]


def build_query(title: str, description: str | None, llm_enabled: bool = True) -> tuple[str, bool]:
    text = f"{title} {description or ''}".strip()
    normalized = text.lower()
    is_bulk = any(marker in normalized for marker in BULK_MARKERS)

    clean = text
    for pattern in NOISE_PATTERNS:
        clean = re.sub(pattern, " ", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s+", " ", clean).strip()
    tokens = clean.split(" ")
    query = " ".join(tokens[:12])
    if llm_enabled:
        # Placeholder for future model enrichment; currently deterministic.
        return query, is_bulk
    return query, is_bulk
