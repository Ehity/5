"""Детекция периодичности списаний внутри кластера: ежемесячно / ежегодно."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd

# Допуски интервалов, дней
MONTHLY_RANGE = (25, 35)
ANNUAL_RANGE = (340, 390)
AMOUNT_TOLERANCE = 0.15  # разброс сумм внутри подписки (комиссии, округления)
MIN_CHARGES = 2          # минимум списаний, чтобы считать подпиской
MIN_CONFIDENCE_CHARGES = 3  # с этого числа уверенностей "высокая"


@dataclass
class Subscription:
    cluster_id: int
    title: str
    variants: list[str] = field(default_factory=list)
    period: str = "monthly"          # monthly | annual
    median_amount: float = 0.0
    charges: int = 0
    first_date: datetime | None = None
    last_date: datetime | None = None
    next_date: datetime | None = None
    monthly_cost: float = 0.0        # для annual = сумма / 12
    confidence: str = "low"          # low | medium | high

    def to_dict(self) -> dict:
        return {
            "Подписка": self.title,
            "Периодичность": "ежемесячно" if self.period == "monthly" else "ежегодно",
            "Списание": round(self.median_amount, 2),
            "В месяц": round(self.monthly_cost, 2),
            "Списаний": self.charges,
            "Последнее": self.last_date.strftime("%d.%m.%Y") if self.last_date is not None else "",
            "Следующее": self.next_date.strftime("%d.%m.%Y") if self.next_date is not None else "",
            "Уверенность": self.confidence,
        }


def _gaps_days(dates: pd.Series) -> np.ndarray:
    d = dates.sort_values().reset_index(drop=True)
    return np.array([(d[i + 1] - d[i]).days for i in range(len(d) - 1)], dtype=float)


def detect_periodicity(tx: pd.DataFrame, cluster_id: int, title: str,
                       variants: list[str]) -> Subscription | None:
    """Пытается найти подписку в транзакциях одного кластера.

    tx: колонки date (datetime), amount (float), description (str).
    Возвращает Subscription или None, если периодичность не подтверждается.
    """
    tx = tx.sort_values("date").reset_index(drop=True)
    if len(tx) < MIN_CHARGES:
        return None

    # Медичные суммы устойчивы к копеечному дрожанию; отбрасываем выбросы сумм
    median_amount = float(tx["amount"].median())
    tx = tx[tx["amount"].between(median_amount * (1 - AMOUNT_TOLERANCE),
                                 median_amount * (1 + AMOUNT_TOLERANCE))]
    if len(tx) < MIN_CHARGES:
        return None

    gaps = _gaps_days(tx["date"])
    med_gap = float(np.median(gaps))

    if MONTHLY_RANGE[0] <= med_gap <= MONTHLY_RANGE[1]:
        period = "monthly"
    elif ANNUAL_RANGE[0] <= med_gap <= ANNUAL_RANGE[1]:
        period = "annual"
    else:
        return None  # нерегулярные списания — не подписка

    dates = tx["date"].tolist()
    offset = pd.DateOffset(months=1) if period == "monthly" else pd.DateOffset(years=1)
    next_date = pd.Timestamp(dates[-1]) + offset
    confidence = ("high" if len(tx) >= MIN_CONFIDENCE_CHARGES + 1 and
                  np.all(np.abs(gaps - med_gap) <= 5) else
                  "medium" if len(tx) >= MIN_CONFIDENCE_CHARGES else "low")

    return Subscription(
        cluster_id=cluster_id,
        title=title,
        variants=variants,
        period=period,
        median_amount=median_amount,
        charges=len(tx),
        first_date=dates[0],
        last_date=dates[-1],
        next_date=next_date,
        monthly_cost=median_amount if period == "monthly" else median_amount / 12,
        confidence=confidence,
    )
