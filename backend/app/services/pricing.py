from __future__ import annotations


def all_in_cost(
    bid: float | None,
    buyers_premium_pct: float | None,
    tax_rate: float,
    shipping_estimate: float,
) -> float | None:
    if bid is None:
        return None
    premium = buyers_premium_pct or 0.0
    subtotal = bid * (1 + premium)
    taxed = subtotal * (1 + tax_rate)
    return round(taxed + shipping_estimate, 2)


def margin_indicator(all_in: float | None, market_low: float | None, market_median: float | None, target_margin_pct: float) -> str:
    if all_in is None or market_low is None:
        return "grey"
    target = all_in * (1 + target_margin_pct)
    if market_low >= target:
        return "green"
    if market_median is not None and market_median >= target:
        return "amber"
    return "red"
