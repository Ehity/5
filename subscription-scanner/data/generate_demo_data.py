"""Генератор демонстрационной выписки за 6 месяцев.

Создаёт реалистичный CSV с подписками и «ловушками» из кейса:
- один сервис под разными названиями (NETFLIX.COM / NFLX* / Netflix);
- годовая подписка (iCloud+);
- пропуск месяца (ivi) для проверки устойчивости;
- шум: продукты, переводы, АЗС и т.п.

Запуск:  python data/generate_demo_data.py [выход.csv]
"""

from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

SEED = 42


def month_shift(base: date, months: int) -> date:
    """Дата через months месяцев от base (день сохраняется, где возможно)."""
    m = base.month - 1 + months
    year = base.year + m // 12
    month = m % 12 + 1
    day = min(base.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                         31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return date(year, month, day)


def gen_noise(rng: random.Random, start: date, end: date) -> list[dict]:
    """Бытовой шум: продуктовые магазины, маркетплейсы, АЗС, переводы."""
    merchants = [
        ("ПЯТЕРОЧКА", (250, 2500)), ("ВКУСВИЛЛ", (400, 1800)),
        ("WILDBERRIES", (900, 7000)), ("OZON.RU", (500, 5500)),
        ("АЗС ЛУКОЙЛ", (1200, 3200)), ("АПТЕКА 36,6", (300, 1500)),
        ("САМКАТ СИТИ", (200, 900)), ("ПЕРЕКРЕСТОК", (600, 3400)),
        ("ЯНДЕКС ТАКСИ", (250, 900)), ("КОФЕЙНЯ ДАБЛБИ", (250, 550)),
    ]
    rows = []
    d = start
    while d <= end:
        if rng.random() < 0.75:
            name, (lo, hi) = rng.choice(merchants)
            rows.append({"date": d, "amount": round(rng.uniform(lo, hi), 2), "description": name})
        d += timedelta(days=1)
    return rows


def build_statement() -> list[dict]:
    rng = random.Random(SEED)
    end = date.today()
    start = month_shift(end, -6)
    rows: list[dict] = []

    def add(d: date, amount: float, desc: str) -> None:
        rows.append({"date": d, "amount": amount, "description": desc})

    # --- Netflix: один сервис, три варианта названия мерчанта (ловушка кейса) ---
    netflix_variants = ["NETFLIX.COM 866-579-7172 US", "NFLX* B8R2K3P4 866-579-7172", "Netflix"]
    for i in range(7):
        d = month_shift(start, i)
        if d > end:
            break
        add(d, 599.00, rng.choice(netflix_variants))

    # --- Кинопоиск: стабильная ежемесячная сумма ---
    for i in range(7):
        d = month_shift(start, i)
        if d <= end:
            add(d, 399.00, "КИНОПОИСК ПЛЮС HD МОСКВА")

    # --- Яндекс Плюс ---
    for i in range(7):
        d = month_shift(start, i)
        if d <= end:
            add(d, 299.00, "ЯНДЕКС.ПЛЮС")

    # --- Spotify: варианты названия + копеечная комиссия ---
    for i in range(7):
        d = month_shift(start, i)
        if d > end:
            break
        desc = rng.choice(["SPOTIFY MUSIC STOCKHOLM", "SPOTIFY MUSIC AB"])
        add(d, 269.00 if i % 3 else 272.41, desc)

    # --- ivi: пропуск месяца (апрель) для проверки устойчивости детекта ---
    skip = month_shift(start, 1).month
    for i in range(7):
        d = month_shift(start, i)
        if d > end or d.month == skip:
            continue
        add(d, 299.00, "IVI.RU ONLINE КИНОТЕАТР")

    # --- Фитнес: дорогой ежемесячный абонемент ---
    for i in range(7):
        d = month_shift(start, i)
        if d <= end:
            add(d, 3490.00, "АБОНЕМЕНТ WORLD CLASS ФИТНЕС")

    # --- Годовая подписка iCloud+ 2TB ---
    add(month_shift(start, 1), 2990.00, "ICLOUD+ 2TB APPLE.COM/BILL")

    # --- Разовые покупки, маскирующиеся под подписку (не периодичны) ---
    add(month_shift(start, 2), 499.00, "ДОНАТ GAME STORE")
    add(month_shift(start, 4), 498.00, "STEAM PURCHASE")

    rows.extend(gen_noise(rng, start, end))
    rows.sort(key=lambda r: r["date"])
    return rows


def save_csv(path: Path) -> Path:
    import pandas as pd  # локальный импорт: скрипт можно посмотреть без pandas

    rows = build_statement()
    df = pd.DataFrame(rows)
    df["date"] = df["date"].astype(str)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig", sep=";")
    return path


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "demo_statement.csv"
    p = save_csv(out)
    print(f"Демо-выписка сохранена: {p} ({len(build_statement())} транзакций)")
