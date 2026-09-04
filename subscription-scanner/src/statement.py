"""Загрузка и нормализация банковской выписки (CSV)."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

# Возможные имена колонок в выписках разных банков
COLUMN_ALIASES = {
    "date": ["date", "дата операции", "дата", "дата платежа", "operation date"],
    "amount": ["amount", "сумма", "сумма платежа", "сумма операции", "списание"],
    "description": ["description", "описание", "назначение", "назначение платежа",
                    "контрагент", "merchant", "получатель"],
}


def _match_column(col: str, kind: str) -> bool:
    c = re.sub(r"[^a-zа-я ]", "", str(col).strip().lower())
    return c in COLUMN_ALIASES[kind]


def load_statement(path: str | Path) -> pd.DataFrame:
    """Читает выписку и приводит к виду: date (datetime), amount (float > 0), description (str).

    Поддерживает CSV с любым из разделителей ; , \t и кодировки utf-8 / cp1251.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Файл выписки не найден: {path}")

    last_err: Exception | None = None
    df = None
    for enc in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            df = pd.read_csv(path, sep=None, engine="python", encoding=enc, nrows=None)
            break
        except UnicodeDecodeError as e:  # пробуем следующую кодировку
            last_err = e
    if df is None:
        raise ValueError(f"Не удалось прочитать файл: {last_err}")

    rename = {}
    for col in df.columns:
        for kind in COLUMN_ALIASES:
            if kind not in rename and _match_column(col, kind):
                rename[col] = kind
    df = df.rename(columns=rename)

    missing = {"date", "amount", "description"} - set(df.columns)
    if missing:
        raise ValueError(f"В выписке не найдены колонки: {sorted(missing)}; есть: {list(df.columns)}")

    df = df[["date", "amount", "description"]].copy()
    # ISO-даты ("2026-03-04") парсим как есть; dayfirst ломает их в pandas 2.x,
    # поэтому dayfirst включаем только если обычный парсинг даёт много пропусков
    parsed = pd.to_datetime(df["date"], errors="coerce")
    if parsed.isna().mean() > 0.5:
        parsed = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df["date"] = parsed
    df["amount"] = pd.to_numeric(
        df["amount"].astype(str).str.replace(r"[^\d.,-]", "", regex=True)
        .str.replace(",", ".", regex=False),
        errors="coerce",
    )
    df["description"] = df["description"].astype(str).str.strip()

    df = df.dropna(subset=["date", "amount"])
    df = df[df["amount"] > 0]  # только списания
    df["description"] = df["description"].replace({"nan": ""})
    df = df[df["description"] != ""]
    return df.sort_values("date").reset_index(drop=True)
