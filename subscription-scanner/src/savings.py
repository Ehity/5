"""Расчёт экономии при отказе от подписок."""

from __future__ import annotations

from dataclasses import dataclass

from .periodicity import Subscription


@dataclass
class SavingsReport:
    cancelled: list[Subscription]
    yearly_total: float

    def to_dict(self) -> dict:
        rows = []
        for s in self.cancelled:
            yearly = s.monthly_cost * 12
            rows.append({
                "Подписка": s.title,
                "В месяц": round(s.monthly_cost, 2),
                "Экономия за год": round(yearly, 2),
            })
        return {"items": rows, "yearly_total": round(self.yearly_total, 2)}


def compute_savings(subscriptions: list[Subscription],
                    to_cancel: list[str]) -> SavingsReport:
    """to_cancel — подстроки названий (без учёта регистра)."""
    keys = [c.lower().strip() for c in to_cancel]
    cancelled = [
        s for s in subscriptions
        if any(k in s.title.lower() or k in " ".join(s.variants).lower() for k in keys)
    ]
    yearly = sum(s.monthly_cost * 12 for s in cancelled)
    return SavingsReport(cancelled=cancelled, yearly_total=yearly)
