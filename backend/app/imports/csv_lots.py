from __future__ import annotations

import csv
from dataclasses import dataclass

from app.adapters.base import LotRecord
from app.adapters.helpers import parse_price
from app.config import settings


@dataclass
class ParsedLotImport:
    lots: list[LotRecord]
    warnings: list[str]


def _pick(row: dict[str, str], *names: str) -> str | None:
    lowered = {k.strip().lower(): (v or "").strip() for k, v in row.items()}
    for name in names:
        value = lowered.get(name)
        if value:
            return value
    return None


def parse_lots_csv(csv_text: str, max_items: int) -> ParsedLotImport:
    warnings: list[str] = []
    lots: list[LotRecord] = []

    reader = csv.DictReader(csv_text.splitlines())
    if not reader.fieldnames:
        return ParsedLotImport(lots=[], warnings=["CSV appears empty or missing a header row."])

    for idx, row in enumerate(reader, start=2):
        if len(lots) >= max_items:
            break

        title = _pick(row, "title", "name", "lot title")
        if not title:
            warnings.append(f"Row {idx} skipped: missing title.")
            continue

        current_bid = parse_price(_pick(row, "current_bid", "current bid", "bid", "price"))
        opening_bid = parse_price(_pick(row, "opening_bid", "opening bid", "start bid", "quick bid"))
        estimate_low = parse_price(_pick(row, "estimate_low", "estimate low", "low estimate"))
        estimate_high = parse_price(_pick(row, "estimate_high", "estimate high", "high estimate"))

        lots.append(
            LotRecord(
                lot_number=_pick(row, "lot_number", "lot number", "lot"),
                title=title,
                description=_pick(row, "description", "desc"),
                image_url=_pick(row, "image_url", "image", "image url"),
                current_bid=current_bid,
                opening_bid=opening_bid,
                estimate_low=estimate_low,
                estimate_high=estimate_high,
                currency=_pick(row, "currency") or settings.default_currency,
                buyers_premium_pct=parse_price(_pick(row, "buyers_premium_pct", "buyers premium", "premium")),
                ends_at=_pick(row, "ends_at", "ends at", "end time"),
                lot_url=_pick(row, "lot_url", "url", "lot url"),
                raw={"source": "manual_csv", "row": idx},
                confidence=0.85,
            )
        )

    if not lots and not warnings:
        warnings.append("No valid lot rows were found in CSV.")

    return ParsedLotImport(lots=lots, warnings=warnings)
