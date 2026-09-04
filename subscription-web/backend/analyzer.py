"""Анализ выписки: парсинг CSV, поиск регулярных платежей, нормализация названий."""

from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime, timedelta

# ---------------------------------------------------------------------------
# Нормализация названий: объединяем 'YNDX_PLUS', 'YNDX.MUSIC', 'ЯНДЕКС' в
# одну подписку «Яндекс Плюс» и т.п.
# ---------------------------------------------------------------------------
# (каноничное имя, категория, emoji-иконка, ключевые слова в любом регистре)
BRAND_RULES = [
    # «Яндекс Плюс» — только точечные ключи (общий «ЯНДЕКС» ловит и такси/кино)
    ("Яндекс Плюс", "Развлечения", "🟡",
     ["YNDX", "YANDEX_PLUS", "YANDEX PLUS", "ЯНДЕКС.ПЛЮС", "ЯНДЕКС ПЛЮС", "ЯНДЕКС+"]),
    ("Netflix", "Кино и видео", "🎬",
     ["NETFLIX", "NFLX"]),
    ("Иви", "Кино и видео", "🍿",
     ["IVI"]),
    ("Кинопоиск", "Кино и видео", "🎥",
     ["КИНОПОИСК", "KINOPOISK"]),
    ("Spotify", "Музыка", "🎧",
     ["SPOTIFY", "SPOT*"]),
    ("WORLD CLASS", "Фитнес", "🏋️",
     ["WORLD CLASS", "WORLDCLASS", "ФИТНЕС"]),
    ("iCloud+", "Облако", "☁️",
     ["ICLOUD", "APPLE.COM/BILL"]),
    ("VK Музыка", "Музыка", "🎵",
     ["VK MUZ", "VK MUSIC", "МУЗЫКА VK"]),
    ("YouTube Premium", "Развлечения", "▶️",
     ["YOUTUBE"]),
    ("СберПрайм", "Экосистема", "🟢",
     ["СБЕРПРАЙМ", "SBERPRIME", "ПРАЙМ"]),
]

ABBREV_MAP = {"NFLX": "NETFLIX", "SPOT": "SPOTIFY", "YNDX": "YANDEX"}


def canonical_name(description: str) -> tuple[str, str, str] | None:
    """Возвращает (название, категория, иконка) или None, если бренд не опознан."""
    s = str(description).upper()
    for name, cat, icon, keys in BRAND_RULES:
        if any(k in s for k in keys):
            return name, cat, icon
    return None


def normalize_description(desc: str) -> str:
    """Нормализация для fallback-группировки безымянных мерчантов."""
    s = str(desc).upper()
    s = re.sub(r"HTTPS?://\S+|WWW\.\S+", " ", s)
    s = re.sub(r"\S*\d\S*", " ", s)            # токены с цифрами
    s = re.sub(r"\.[A-ZА-ЯЁ]{2,3}\b", " ", s)  # домены
    s = re.sub(r"[^A-ZА-ЯЁ ]+", " ", s)
    tokens = [ABBREV_MAP.get(t, t) for t in s.split() if len(t) >= 2]
    return " ".join(tokens).strip()


# ---------------------------------------------------------------------------
# Парсинг CSV
# ---------------------------------------------------------------------------
COLUMN_ALIASES = {
    "date": ["date", "дата", "дата операции", "дата платежа"],
    "amount": ["amount", "сумма", "сумма платежа", "списание", "charges"],
    "description": ["description", "описание", "назначение", "контрагент", "получатель", "merchant"],
}


def _parse_date(s: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_csv(content: bytes) -> list[dict]:
    """Читает CSV-выписку -> [{'date': date, 'amount': float, 'description': str}]."""
    text = None
    for enc in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ValueError("Не удалось определить кодировку файла")

    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.DictReader(io.StringIO(text), dialect=dialect))
    if not rows:
        return []

    cols = {k.lower().strip(): k for k in rows[0]}
    pick = {}
    for kind, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in cols:
                pick[kind] = cols[alias]
                break
    if set(pick) != {"date", "amount", "description"}:
        raise ValueError(f"В CSV нет нужных колонок, найдены: {list(rows[0].keys())}")

    txs = []
    for row in rows:
        d = _parse_date(str(row[pick["date"]]).strip())
        try:
            amount = float(re.sub(r"[^\d.,-]", "", str(row[pick["amount"]])).replace(",", "."))
        except ValueError:
            continue
        desc = str(row[pick["description"]]).strip()
        if amount != 0 and desc and d:
            txs.append({"date": d, "amount": amount, "description": desc})
    txs.sort(key=lambda t: t["date"])
    return txs


# ---------------------------------------------------------------------------
# Парсинг PDF-выписки (формат Сбербанк Онлайн: дата/время → сумма → описание)
# ---------------------------------------------------------------------------
# Строки-заглушки (шапки, итоги, нумерация страниц) — не описания транзакций
_PDF_SKIP_RE = re.compile(
    r"продолжение|страниц|сформирова|справк|выписк|счёт|счет|доступн|"
    r"баланс|всего|итого|период|владелец|операци|статус|реквизит|валюта|назначение",
    re.IGNORECASE,
)
_DATE_RE = re.compile(r"\b(\d{2}[./]\d{2}[./]\d{2,4})\b")
_TIME_ONLY_RE = re.compile(r"^[\d\s:.]+$")
_TIME_IN_DESC_RE = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")

# Строгий: обязательны знак и суффикс валюты (формат СберБанк Онлайн)
_MONEY_STRICT = re.compile(
    r"(?P<sign>[+−–-])\s*(?P<whole>[\d\u00a0 ]+?)(?:[.,](?P<frac>\d{1,2}))?\s*"
    r"(?:₽|руб\.?|руб|RUB)",
    re.IGNORECASE,
)
# Свободный: для выписок, где суммы без знака/суффикса. Исключаем телефоны и даты:
# подходит число с пробелом-разделителем тысячи ИЛИ со знаком ИЛИ с суффиксом валюты.
_MONEY_LOOSE = re.compile(
    r"(?<![0-9.,])(?:(?P<sign>[+−–-])\s*)?(?P<whole>[\d\u00a0 ]{2,})(?:[.,](?P<frac>\d{1,2}))?"
    r"\s*(?P<curr>₽|руб\.?|руб|RUB)?(?![0-9])",
    re.IGNORECASE,
)


def _parse_money(s: str, strict: bool) -> tuple[str, float | None]:
    """Возвращает (знак, сумма). Пример: '-599,00 ₽' → ('-', 599.0)."""
    pattern = _MONEY_STRICT if strict else _MONEY_LOOSE
    m = pattern.search(s)
    if not m:
        return "", None
    sign = (m.group("sign") or "").strip()
    curr = m.group("curr") if "curr" in m.groupdict() and m.group("curr") else ""
    whole = (m.group("whole") or "").replace(" ", "").replace("\u00a0", "")
    frac = m.group("frac")
    try:
        value = float(whole)
    except ValueError:
        return "", None
    # свободный режим: отсеиваем телефоны и даты («866-579-7172», «05.02.2026»)
    if not strict and not (sign or curr or (" " in whole or "\u00a0" in whole)):
        return "", None
    if frac:
        value += int(frac) / (10 ** len(frac))
    return sign, round(value, 2)


def parse_pdf(content: bytes) -> list[dict]:
    """Извлекает транзакции из текстового PDF-выписки (формат Сбербанк Онлайн)."""
    import io as _io

    import pdfplumber

    lines: list[str] = []
    with pdfplumber.open(_io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines.extend(l.strip() for l in text.splitlines() if l.strip())
    return _transactions_from_lines(lines)


def _transactions_from_lines(lines: list[str]) -> list[dict]:
    """Собирает транзакции из строк выписки.

    Поддерживает два формата:
      1) многострочный (Сбер):  '05.08.26 17:04' / '−599,00 ₽' / 'NETFLIX.COM ...'
      2) однострочный:          '05.08.2026  NETFLIX.COM  -599,00 ₽'
    """
    has_currency = any(("₽" in l or "руб" in l or "RUB" in l) for l in lines)
    strict = has_currency  # строгий режим — если в выписке есть знак валюты

    # если в выписке есть хоть один минус — берём только списания,
    # иначе (все суммы без знака) — берём всё (разделить нельзя)
    saw_signed = any(
        _parse_money(l, strict)[0] in "−–-" for l in lines
    )

    txs: list[dict] = []
    pending: dict | None = None  # {'date': date, 'amount': float|None, 'desc': [str]}

    def flush() -> None:
        nonlocal pending
        if pending and pending["amount"] is not None:
            desc = re.sub(r"\s+", " ", " ".join(pending["desc"])).strip(" -–−.")
            desc = _DATE_RE.sub(" ", desc)
            desc = _TIME_IN_DESC_RE.sub(" ", desc)
            desc = re.sub(r"\s+", " ", desc).strip(" -–−.")
            if desc:
                txs.append({"date": pending["date"], "amount": pending["amount"],
                            "description": desc[:120]})
        pending = None

    def start_tx(d: date, amount: float | None, desc_part: str = "") -> None:
        nonlocal pending
        pending = {"date": d, "amount": amount, "desc": []}
        if desc_part and not _PDF_SKIP_RE.search(desc_part):
            pending["desc"].append(desc_part)

    for line in lines:
        m_date = _DATE_RE.search(line)
        sign, amount = _parse_money(line, strict)
        is_skip = bool(_PDF_SKIP_RE.search(line))
        has_money = amount is not None

        if m_date and has_money:
            # однострочный формат: дата + (описание) + сумма
            flush()
            d = _parse_date(m_date.group(1))
            if not d:
                continue
            # описание между датой и суммой
            m_money = (_MONEY_STRICT if strict else _MONEY_LOOSE).search(line)
            desc = (line[:m_date.start()] + " " + line[m_date.end():m_money.start()])
            desc = _TIME_IN_DESC_RE.sub(" ", desc)
            desc = re.sub(r"\s+", " ", desc).strip(" -–−.")
            debit = sign in "−–-"
            if desc and not _TIME_ONLY_RE.fullmatch(desc):
                if amount is not None and (debit or not saw_signed):
                    txs.append({"date": d, "amount": amount, "description": desc[:120]})
            else:
                # дата + сумма, описание пойдёт следующими строками
                start_tx(d, amount if (debit or not saw_signed) else None)
            continue

        if m_date:
            # новая транзакция начинается (дата/время на отдельной строке)
            flush()
            d = _parse_date(m_date.group(1))
            if d and not is_skip:
                rest = line[m_date.end():].strip()
                start_tx(d, None, rest if not _TIME_ONLY_RE.fullmatch(rest) else "")
            continue

        if has_money:
            # строка суммы текущей транзакции (или итог/баланс внизу)
            if pending is not None and not is_skip:
                debit = sign in "−–-"
                pending["amount"] = amount if (debit or not saw_signed) else None
            continue

        # обычная строка: продолжение описания или шапка/шум
        if pending is not None and not is_skip and not _TIME_ONLY_RE.fullmatch(line):
            pending["desc"].append(line)

    flush()

    result = sorted(txs, key=lambda t: t["date"])
    return result

def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    year = d.year + m // 12
    month = m % 12 + 1
    day = min(d.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                      31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return date(year, month, day)


def detect_subscriptions(txs: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for t in txs:
        canon = canonical_name(t["description"])
        key = ("brand", canon[0]) if canon else ("norm", normalize_description(t["description"]))
        groups.setdefault(key, []).append(t)

    subs = []
    for key, items in groups.items():
        if len(items) < 3:  # минимум 3 списания, чтобы отличать подписку от случайных совпадений
            continue
        amounts = sorted(i["amount"] for i in items)
        median = amounts[len(amounts) // 2]
        stable = [i for i in items if abs(i["amount"] - median) <= abs(median) * 0.15]
        if len(stable) < 3:
            continue
        stable.sort(key=lambda t: t["date"])
        gaps = sorted((stable[i + 1]["date"] - stable[i]["date"]).days
                      for i in range(len(stable) - 1))
        # списания в один день (разные варианты мерчанта) дают gap 0 и ломают
        # медиану — отбрасываем их, оставляя «настоящие» интервалы между периодами
        gaps = [g for g in gaps if g >= 10]
        if not gaps:
            continue
        med_gap = gaps[len(gaps) // 2]

        if 20 <= med_gap <= 40:
            period = "monthly"
        elif 340 <= med_gap <= 390:
            period = "annual"
        else:
            continue

        last = stable[-1]["date"]
        monthly = median if period == "monthly" else median / 12
        title = key[1] if key[0] == "brand" else key[1].title() or "Подписка"
        name, cat, icon = canonical_name(stable[-1]["description"]) or (title, "Прочее", "💳")
        subs.append({
            "id": re.sub(r"\W+", "_", title.lower())[:40] or "sub",
            "name": name if key[0] == "brand" else title,
            "category": cat,
            "icon": icon,
            "amount": round(median, 2),
            "period": "ежемесячно" if period == "monthly" else "ежегодно",
            "monthly_cost": round(monthly, 2),
            "yearly_cost": round(monthly * 12, 2),
            "charges": len(stable),
            "first_charge": stable[0]["date"].isoformat(),
            "last_charge": last.isoformat(),
            "next_charge": _add_months(last, 1 if period == "monthly" else 12).isoformat(),
            "merchants": sorted({t["description"] for t in stable}),
        })
    subs.sort(key=lambda s: -s["monthly_cost"])
    return subs


def monthly_expense_series(subs: list[dict], months: int = 6) -> list[dict]:
    """Расходы на подписки по месяцам (для графика)."""
    today = date.today()
    series = []
    for i in range(months - 1, -1, -1):
        d = _add_months(today.replace(day=1), -i)
        total = 0.0
        for s in subs:
            cur = date.fromisoformat(s["first_charge"])
            for _ in range(240):
                if cur > d:
                    break
                if cur.month == d.month and cur.year == d.year:
                    total += s["monthly_cost"]
                cur = _add_months(cur, 1)
        series.append({"month": d.strftime("%m.%Y"), "spent": round(total, 2)})
    return series


def monthly_expense_series_all(txs: list[dict], months: int = 6) -> list[dict]:
    """Реальные списания по месяцам из ВСЕХ транзакций (не только подписки).

    Строит график общих расходов по выписке, когда подписок не найдено.
    """
    today = date.today()
    series = []
    for i in range(months - 1, -1, -1):
        d = _add_months(today.replace(day=1), -i)
        total = 0.0
        for t in txs:
            td = t["date"]
            if td.year == d.year and td.month == d.month:
                total += t["amount"]
        series.append({"month": d.strftime("%m.%Y"), "spent": round(total, 2)})
    return series


# ---------------------------------------------------------------------------
# Демо-данные (fallback, чтобы UI всегда был готов к презентации)
# ---------------------------------------------------------------------------
def demo_payload() -> dict:
    today = date.today()

    subs = [
        _demo_sub("world_class", "WORLD CLASS", "Фитнес", "🏋️", 3490.0, today, -7, 23),
        _demo_sub("netflix", "Netflix", "Кино и видео", "🎬", 599.0, today, -7, 23),
        _demo_sub("yandex_plus", "Яндекс Плюс", "Развлечения", "🟡", 399.0, today, -7, 23),
        _demo_sub("ivi", "Иви", "Кино и видео", "🍿", 299.0, today, -7, 23),
        _demo_sub("icloud", "iCloud+", "Облако", "☁️", 149.0, today, -7, 23),
    ]
    total_monthly = round(sum(s["monthly_cost"] for s in subs), 2)
    series = []
    for i in range(5, -1, -1):
        d = _add_months(today.replace(day=1), -i)
        jitter = [4936, 4936, 5235, 4936, 5335, 4936][5 - i]
        series.append({"month": d.strftime("%m.%Y"), "spent": jitter})

    return {
        "mock": True,
        "subscriptions": subs,
        "monthly": series,
        "total_monthly": total_monthly,
        "total_yearly": round(total_monthly * 12, 2),
        "message": "Показаны демонстрационные данные — загрузите CSV-выписку для анализа своей",
    }


def _demo_sub(sid, name, category, icon, amount, today, last_shift, next_shift):
    first_charge = _add_months(today, -5)
    return {
        "id": sid, "name": name, "category": category, "icon": icon,
        "amount": amount, "period": "ежемесячно",
        "monthly_cost": amount, "yearly_cost": round(amount * 12, 2),
        "charges": 6,
        "first_charge": first_charge.isoformat(),
        "last_charge": (today + timedelta(days=last_shift)).isoformat(),
        "next_charge": (today + timedelta(days=next_shift)).isoformat(),
        "merchants": [],
    }
