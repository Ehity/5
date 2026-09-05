"""Анализ выписки: парсинг CSV, поиск регулярных платежей, нормализация названий."""

from __future__ import annotations

import csv
import io
import random
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
     ["YNDX", "YANDEX_PLUS", "YANDEX PLUS", "ЯНДЕКС.ПЛЮС", "ЯНДЕКС ПЛЮС",
      "ЯНДЕКС+", "YANDEX.MUSIC", "ПЛЮС МУЗЫК", "МУЗЫКА ПЛЮС"]),
    ("Netflix", "Кино и видео", "🎬",
     ["NETFLIX", "NFLX"]),
    ("Иви", "Кино и видео", "🍿",
     ["IVI", "ИВИ"]),
    ("Кинопоиск", "Кино и видео", "🎥",
     ["КИНОПОИСК", "KINOPOISK", "KP*"]),
    ("Okko", "Кино и видео", "🎞️",
     ["OKKO", "ОККО"]),
    ("KION", "Кино и видео", "🎬",
     ["KION", "КИОН"]),
    ("Premier", "Кино и видео", "📺",
     ["PREMIER", "ПРЕМЬЕР"]),
    ("Амедиатека", "Кино и видео", "🍿",
     ["AMEDIATEKA", "АМЕДИАТЕКА"]),
    ("More.tv", "Кино и видео", "📺",
     ["MORE.TV", "MORETV", "МОР ТВ"]),
    ("Start", "Кино и видео", "▶️",
     ["START.RU", "START TV"]),
    ("Wink", "Кино и видео", "📺",
     ["WINK", "ВИНК"]),
    ("Megogo", "Кино и видео", "🎬",
     ["MEGOGO", "МЕГОГО"]),
    ("Spotify", "Музыка", "🎧",
     ["SPOTIFY", "SPOT*"]),
    ("Звук", "Музыка", "🎵",
     ["ЗВУК", "ZVUK"]),
    ("Apple Music", "Музыка", "🍎",
     ["APPLE MUSIC", "APPLE.COM/BILLAPPLEMUSIC"]),
    ("VK Музыка", "Музыка", "🎵",
     ["VK MUZ", "VK MUSIC", "МУЗЫКА VK", "VK.COM/MUSIC", "VK.COM", "SUBSCRIPTION VK"]),
    ("YouTube Premium", "Развлечения", "▶️",
     ["YOUTUBE", "GOOGLE*YOUTUBE"]),
    ("Telegram Premium", "Мессенджеры", "✈️",
     ["TG_PREMIUM", "TELEGRAM PREMIUM", "PREMIUMBOT", "T.G PREMIUM", "TEL.EGRAM"]),
    ("WORLD CLASS", "Фитнес", "🏋️",
     ["WORLD CLASS", "WORLDCLASS", "ФИТНЕС", "WORLD CLUB"]),
    ("СберПрайм", "Экосистема", "🟢",
     ["СБЕРПРАЙМ", "SBERPRIME", "ПРАЙМ"]),
    ("Яндекс Go", "Транспорт", "🚕",
     ["YANDEX GO", "ЯНДЕКС ТАКСИ", "ЯНДЕКС ГО", "TAXI"]),
    ("iCloud+", "Облако", "☁️",
     ["ICLOUD", "APPLE.COM/BILL"]),
    ("Google One", "Облако", "🌐",
     ["GOOGLE ONE", "GOOGLE ONEAI"]),
    ("Microsoft 365", "ПО", "💻",
     ["MICROSOFT 365", "MICROSOFT OFFICE", "OFFICE 365"]),
    ("Adobe", "ПО", "🎨",
     ["ADOBE", "CREATIVE CLOUD"]),
    ("Canva Pro", "Дизайн", "🎨",
     ["CANVA"]),
    ("Figma", "Дизайн", "🎨",
     ["FIGMA"]),
    ("Notion", "ПО", "🗂️",
     ["NOTION"]),
]


ABBREV_MAP = {"NFLX": "NETFLIX", "SPOT": "SPOTIFY", "YNDX": "YANDEX"}

STOP_WORDS = {"RU", "US", "COM", "ORG", "NET", "HTTP", "HTTPS", "WWW", "THE", "AND", "FOR", "LLC", "INC", "LTD", "GMBH"}



def canonical_name(description: str) -> tuple[str, str, str] | None:
    """Возвращает (название, категория, иконка) или None, если бренд не опознан."""
    s = str(description).upper()
    for name, cat, icon, keys in BRAND_RULES:
        if any(k in s for k in keys):
            return name, cat, icon
    return None


def normalize_description(desc: str) -> str:
    s = str(desc).upper()
    s = re.sub(r"HTTPS?://\\S+|WWW\\.\\S+", " ", s)
    s = re.sub(r"\\S*\\d\\S*", " ", s)            # убираем всё с цифрами
    s = re.sub(r"\\.[\u0410-\u042f\u0401]{2,3}\\b", " ", s)  # домены
    s = re.sub(r"[^A-Z\u0410-\u042f\u0401 ]+", " ", s)
    tokens = [
        ABBREV_MAP.get(t, t)
        for t in s.split()
        if t not in STOP_WORDS and len(t) > 1
    ]
    return " ".join(tokens)


def _parse_date(s: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


COLUMN_ALIASES = {
    "date": ["date", "дата", "дата операции", "дата платежа", "operation date", "transaction date"],
    "amount": ["amount", "сумма", "сумма платежа", "сумма операции", "списание", "value"],
    "description": ["description", "описание", "наименование", "получатель", "merchant", "назначение", "details", "memo"],
    "category": ["category", "категория", "тип"],
}


def _norm_header(h: str) -> str:
    """Нормализуем заголовок: нижний регистр, без скобок/знаков, ё→е."""
    s = str(h).lower().replace("ё", "е")
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^\wа-я ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _pick_columns(rows: list[dict]) -> dict:
    """Ищет колонки: точное совпадение → вхождение → эвристика по данным."""
    headers = list(rows[0])
    norm = {h: _norm_header(h) for h in headers}
    pick: dict[str, str] = {}
    for kind, aliases in COLUMN_ALIASES.items():
        for h in headers:
            if norm[h] in aliases:
                pick[kind] = h
                break
    for kind, aliases in COLUMN_ALIASES.items():
        if kind in pick:
            continue
        for h in headers:
            if len(norm[h]) >= 3 and any(a in norm[h] or norm[h] in a for a in aliases):
                pick[kind] = h
                break

    if not {"date", "amount", "description"}.issubset(pick):
        _guess_columns(rows, headers, pick)
    return pick


_DATE_IN_CELL_RE = re.compile(r"\d{1,4}[./-]\d{1,2}[./-]\d{2,4}")


def _guess_columns(rows: list[dict], headers: list, pick: dict) -> None:
    """Эвристика для нестандартных заголовков: колонка с датами — «дата»,
    колонка с числами — «сумма», самая длинная текстовая — «описание»."""
    sample = rows[:50]
    stats: list[tuple] = []
    for h in headers:
        if h in pick.values():
            continue
        vals = [str(r.get(h, "")) for r in sample if str(r.get(h, "")).strip()]
        if not vals:
            continue
        date_n = sum(1 for v in vals if _DATE_IN_CELL_RE.search(v))
        num_n = 0
        for v in vals:
            try:
                float(re.sub(r"[^\d.,-]", "", v).replace(",", "."))
                num_n += 1
            except ValueError:
                pass
        text_n = sum(len(v) for v in vals) / len(vals)
        stats.append((h, date_n, num_n, text_n))

    if "date" not in pick:
        best = max((s for s in stats if s[1] > 0), key=lambda s: s[1], default=None)
        if best:
            pick["date"] = best[0]
            stats = [s for s in stats if s[0] != best[0]]
    if "amount" not in pick:
        best = max((s for s in stats if s[0] != pick.get("date") and s[2] > 0),
                   key=lambda s: s[2], default=None)
        if best:
            pick["amount"] = best[0]
            stats = [s for s in stats if s[0] != best[0]]
    if "description" not in pick:
        best = max((s for s in stats if s[0] not in (pick.get("date"), pick.get("amount"))),
                   key=lambda s: s[3], default=None)
        if best:
            pick["description"] = best[0]


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

    pick = _pick_columns(rows)
    if not {"date", "amount", "description"}.issubset(pick):
        raise ValueError(
            "Не удалось определить в CSV колонки «Дата / Сумма / Описание». "
            f"Заголовки: {list(rows[0].keys())}"
        )

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
    # строгий режим — только когда в выписке реально есть знак минус в сумме.

    # беззнаковые суммы (напр. "599.0 RUB") парсятся свободным режимом,
    # чтобы тестовые PDF-выписки не теряли транзакции вообще.
    strict = has_currency and any(
        _parse_money(l, True)[0] in "−–-" for l in lines
    )

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


def _dice(a: str, b: str) -> float:
    """Dice-коэффициент по биграммам — примитивная «эмбеддинг»-близость имён."""
    a = a.lower().replace("_", " ").replace(".", " ").replace("*", " ").split()
    b = b.lower().replace("_", " ").replace(".", " ").replace("*", " ").split()
    sa = set("".join(a))
    sb = set("".join(b))
    if not sa or not sb:
        return 0.0
    return 2.0 * len(sa & sb) / (len(sa) + len(sb))


def _canonical_group_key(desc: str) -> tuple:
    """Ключ группы: известный бренд либо нормализованное имя."""
    canon = canonical_name(desc)
    if canon:
        return ("brand", canon[0])
    return ("norm", normalize_description(desc))


def _stable_charges(items: list[dict], tol: float = 0.15) -> tuple[list[dict], float]:
    """Отбирает списания со стабильной ценой: (списания, актуальная цена).

    Суммы кластеризуются с допуском ±15%, так что переживается смена цены
    (первые месяцы по 99 ₽, дальше полные 300 ₽): ценовой уровень участвует,
    если в нём ≥2 списания ИЛИ это самый свежий уровень. Актуальная цена —
    медиана кластера, к которому относится последнее по дате списание.
    """
    by_amount = sorted(items, key=lambda t: t["amount"])
    clusters: list[list[dict]] = [[by_amount[0]]]
    for t in by_amount[1:]:
        base = clusters[-1][len(clusters[-1]) // 2]["amount"]
        if abs(t["amount"] - base) <= abs(base) * tol:
            clusters[-1].append(t)
        else:
            clusters.append([t])

    newest = max(items, key=lambda t: t["date"])
    recurring = [c for c in clusters if len(c) >= 2 or newest in c]
    stable = [t for c in recurring for t in c]
    if not stable:
        return [], 0.0
    stable.sort(key=lambda t: t["date"])

    current_cluster = next(c for c in recurring if stable[-1] in c)
    amounts = sorted(abs(t["amount"]) for t in current_cluster)
    return stable, amounts[len(amounts) // 2]


_PRICE_TOLERANCE = 0.05


def detect_price_change(items: list[dict]) -> dict:
    """Одно подтверждённое изменение цены за историю подписки.

    Смена считается реальной, если на каждом ценовом уровне минимум 2
    списания с допуском ±5% — одиночный «странный» платёж не считается.
    Формат полей совпадает с JS-версией (frontend/src/lib/subscriptionPriceChange.js).
    """
    payments = sorted(
        ({"date": t["date"], "amount": abs(float(t["amount"]))} for t in items),
        key=lambda p: p["date"],
    )
    if len(payments) < 4:
        return {"hasChange": False}

    def same_price(a: float, b: float) -> bool:
        avg = (a + b) / 2
        return avg > 0 and abs(a - b) / avg <= _PRICE_TOLERANCE

    def median(vals: list[float]) -> float:
        s = sorted(vals)
        mid = len(s) // 2
        return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2

    def trailing_level(idx: int) -> tuple[int, float, int]:
        amounts = [payments[idx]["amount"]]
        i = idx - 1
        while i >= 0 and same_price(payments[i]["amount"], median(amounts)):
            amounts.append(payments[i]["amount"])
            i -= 1
        return idx - len(amounts) + 1, median(amounts), len(amounts)

    new_start, new_price, new_count = trailing_level(len(payments) - 1)
    if new_count < 2 or new_start == 0:
        return {"hasChange": False}
    _, old_price, old_count = trailing_level(new_start - 1)
    if old_count < 2 or same_price(old_price, new_price):
        return {"hasChange": False}
    difference = round(new_price - old_price, 2)
    percent = round(difference / old_price * 100, 2)
    if abs(percent) < _PRICE_TOLERANCE * 100:
        return {"hasChange": False}
    return {
        "hasChange": True,
        "direction": "up" if difference > 0 else "down",
        "oldPrice": round(old_price, 2),
        "newPrice": round(new_price, 2),
        "difference": difference,
        "percentChange": percent,
        "changedAt": payments[new_start]["date"].isoformat(),
    }


def detect_subscriptions(txs: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    norm_keys: list[tuple] = []
    for t in txs:
        key = _canonical_group_key(t["description"])
        if key[0] == "norm":
            # эвристика: слепляем близкие нормализованные имена (YNDX_PLUS vs YANDEX PLUS)
            merged = None
            for other in norm_keys:
                if _dice(other[1], key[1]) >= 0.8:
                    merged = other
                    break
            if merged is not None:
                key = merged
            else:
                norm_keys.append(key)
        groups.setdefault(key, []).append(t)

    # Небольшой «glue» между группами: если норм-имя очень близко к бренду — слить бренд
    for norm_key in list(norm_keys):
        for brand_name, _cat, _icons, _keys in BRAND_RULES:
            if _dice(norm_key[1], brand_name) >= 0.75:
                groups.setdefault(("brand", brand_name), []).extend(groups.pop(norm_key, []))
                break

    subs = []
    for key, items in groups.items():
        min_events = 2 if key[0] == "brand" else 3  # брендовые сервисы достаточны уже с 2 списаниями
        if len(items) < min_events:  # минимум списаний, чтобы отличать подписку от случайных совпадений
            continue
        stable, price = _stable_charges(items)
        if len(stable) < min_events:
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
        price = abs(price)
        monthly = price if period == "monthly" else price / 12
        title = key[1] if key[0] == "brand" else key[1].title() or "Подписка"
        name, cat, icon = canonical_name(stable[-1]["description"]) or (title, "Прочее", "💳")
        subs.append({
            "id": re.sub(r"\W+", "_", title.lower())[:40] or "sub",
            "name": name if key[0] == "brand" else title,
            "category": cat,
            "icon": icon,
            "amount": round(price, 2),
            "period": "ежемесячно" if period == "monthly" else "ежегодно",
            "monthly_cost": round(monthly, 2),
            "yearly_cost": round(monthly * 12, 2),
            "charges": len(stable),
            "first_charge": stable[0]["date"].isoformat(),
            "last_charge": last.isoformat(),
            "next_charge": _add_months(last, 1 if period == "monthly" else 12).isoformat(),
            "merchants": sorted({t["description"] for t in stable}),
            "price_change": detect_price_change(items),
        })
    subs.sort(key=lambda s: -abs(s["monthly_cost"]))
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
                if (cur.year, cur.month) > (d.year, d.month):
                    break
                if cur.month == d.month and cur.year == d.year:
                    total += abs(s["monthly_cost"])
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
    rng = random.Random()

    # Слегка варьируем суммы подписок (±10%), чтобы экономия была разной
    subs = [
        _demo_sub("world_class", "WORLD CLASS", "Фитнес", "🏋️", round(3490.0 * rng.uniform(0.9, 1.1), -1), today, -7, 23),
        _demo_sub("netflix", "Netflix", "Кино и видео", "🎬", round(599.0 * rng.uniform(0.9, 1.1), -1), today, -7, 23),
        _demo_sub("yandex_plus", "Яндекс Плюс", "Развлечения", "🟡", round(399.0 * rng.uniform(0.9, 1.1), -1), today, -7, 23),
        _demo_sub("ivi", "Иви", "Кино и видео", "🍿", round(299.0 * rng.uniform(0.9, 1.1), -1), today, -7, 23),
        _demo_sub("icloud", "iCloud+", "Облако", "☁️", round(149.0 * rng.uniform(0.9, 1.1), -1), today, -7, 23),
    ]
    total_monthly = round(sum(s["monthly_cost"] for s in subs), 2)

    # Волнистый график: каждый месяц ±15-30% от базовой суммы
    base = total_monthly
    series = []
    for i in range(5, -1, -1):
        d = _add_months(today.replace(day=1), -i)
        jitter = round(base * rng.uniform(0.7, 1.3), 2)
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
