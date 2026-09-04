import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.periodicity import detect_periodicity


def _tx(dates_amounts):
    return pd.DataFrame([
        {"date": pd.Timestamp(d), "amount": a, "description": "X"}
        for d, a in dates_amounts
    ])


def test_monthly_subscription_detected():
    tx = _tx([("2026-03-05", 599), ("2026-04-05", 599), ("2026-05-05", 599),
              ("2026-06-05", 599), ("2026-07-05", 599)])
    sub = detect_periodicity(tx, 0, "NETFLIX", ["NETFLIX"])
    assert sub is not None
    assert sub.period == "monthly"
    assert sub.median_amount == 599
    assert sub.monthly_cost == 599
    assert sub.next_date == pd.Timestamp("2026-08-05")


def test_monthly_detected_with_missed_month():
    # ivi: пропуск апреля не ломает детект
    tx = _tx([("2026-03-11", 299), ("2026-04-11", 299), ("2026-06-11", 299),
              ("2026-07-11", 299), ("2026-08-11", 299)])
    sub = detect_periodicity(tx, 0, "IVI", ["IVI.RU"])
    assert sub is not None
    assert sub.period == "monthly"
    assert sub.confidence == "medium"  # интервалы неравномерные


def test_annual_subscription_detected():
    tx = _tx([("2025-04-01", 2990), ("2026-04-01", 2990)])
    sub = detect_periodicity(tx, 0, "ICLOUD", ["ICLOUD+ 2TB"])
    assert sub is not None
    assert sub.period == "annual"
    assert sub.monthly_cost == 2990 / 12


def test_irregular_payments_rejected():
    tx = _tx([("2026-03-01", 499), ("2026-03-20", 498), ("2026-05-15", 500)])
    assert detect_periodicity(tx, 0, "GAME", ["GAME STORE"]) is None


def test_single_charge_rejected():
    tx = _tx([("2026-05-01", 299)])
    assert detect_periodicity(tx, 0, "X", ["X"]) is None


def test_outlier_amounts_filtered():
    # крупный выброс суммы не должен менять медиану подписки
    tx = _tx([("2026-03-05", 399), ("2026-04-05", 399), ("2026-05-05", 399),
              ("2026-06-05", 12000)])
    sub = detect_periodicity(tx, 0, "KP", ["КИНОПОИСК"])
    assert sub is not None
    assert sub.median_amount == 399
