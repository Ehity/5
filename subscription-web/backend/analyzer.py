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

# Движение денег между своими счетами и наличные — не подписки, даже если
# повторяются регулярно (карта→вклад, переводы СБП, снятие наличных и т.п.)
_INTERNAL_RE = re.compile(
    r"перевод|банкомат|вклад|наличн|пополнен|списание|сбербанк|стипендия"
    r"|kartavklad|vklad|sberbank onl|qr[- ]?код",
    re.IGNORECASE,
)

# Платежи ЖКХ и бюджетных учреждений (в т.ч. транслит из СБП-выписок: USLU
# = «услуги», UCHREZD = «учреждение») — регулярные, но это не подписки
_UTILITY_RE = re.compile(
    r"жкх|гис жкх|тсж|квартплат|содержан|жиль[яе]|капремонт|капрем|"
    r"водоканал|водоснабж|водоотвед|теплоснабж|теплосеть|энергосбыт|энергосб[у]|"
    r"газпром|межрегионгаз|горгаз|газserv|газserv|еирц|еркц|расч[её]тн|"
    r"домофон|тко|обращен|вывоз|услуг|услу|uslu|uchrezd|учрежд|жилищ| ip |"
    r"домоуправл|жэу|жэк|жилсервис|госуслуг|штраф|гибдд|налог|пошлин",
    re.IGNORECASE,
)

# Покупки в рознице и по QR (даже регулярные и одинаковые) — не подписки.
# Сюда же — обрывки СБП-описаний с городом (MOSKVA/MOSCOW/Ekaterinburg)
_RETAIL_RE = re.compile(
    r"qr|тбанк|т-?банк|t[- ]?банк|tbank|универсальн|альфа|alfa|совком|sovcom|втб|vtb|райф|raif|"
    r"пятер|pyater|красное[ &-]*белое|krasnoe|магнит|magnit|монетк|monetka|"
    r"fixprice|дикси|dixy|лента|lenta|озон|ozon|wildberries|вайлдберр|аптек|apteka|aptech|"
    r"starbucks|старбакс|kfc|макдоналдс|mcdonalds|cinemapark|cinema park|бургер|burger|"
    r"qr[- ]?код|покупк|moskva|moscow|ekaterinburg|перекрест|perekrestok|дэйли|daily|"
    r"вкусно и точка|vkusnoitochka|столовая|кофейн|coffe|coffee",
    re.IGNORECASE,
)


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


def _find_header_line(lines: list[str]) -> int:
    """Выписки Сбера начинаются со служебных строк («900 www.sberbank.ru…»),
    а не с заголовков. Ищем первую строку, где угадываются ≥2 вида колонок."""
    best_idx, best_kinds = 0, 0
    for i, line in enumerate(lines[:15]):
        if not line.strip():
            continue
        for delim in (";", "\t", ","):
            try:
                cells = next(csv.reader([line], delimiter=delim))
            except (csv.Error, StopIteration):
                continue
            if len(cells) < 2:
                continue
            norm = [_norm_header(c) for c in cells]
            kinds = 0
            for aliases in COLUMN_ALIASES.values():
                if any(a in n for n in norm if n for a in aliases):
                    kinds += 1
            if kinds > best_kinds:
                best_idx, best_kinds = i, kinds
        if best_kinds >= 2 and best_idx == i:
            break
    return best_idx


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

    lines = text.splitlines()
    header_idx = _find_header_line(lines)
    body = "\n".join(lines[header_idx:])

    sample = body[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.DictReader(io.StringIO(body), dialect=dialect))
    if not rows:
        return []

    pick = _pick_columns(rows)
    if not {"date", "amount", "description"}.issubset(pick):
        # CSV с одной колонкой — это текстовый дамп выписки (экспорт «как есть»),
        # прогоняем его через построчный PDF-парсер
        if len(rows[0]) == 1:
            text_lines = [next(iter(r.values())).strip().strip('"') for r in rows]
            return _transactions_from_lines(text_lines)
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
    r"баланс|всего|итого|период|владелец|операци|статус|реквизит|валюта|назначение|"
    r"остаток|номер сч|дата откр|дата закрыт|действителен|расшифровк|"
    r"расход|поступлен|кэшб|баланс на",
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


def _money_matches(s: str, strict: bool) -> list[tuple[str, float, int]]:
    """Все валидные суммы в строке: [(знак, значение, позиция)]."""
    out: list[tuple[str, float, int]] = []
    pattern = _MONEY_STRICT if strict else _MONEY_LOOSE
    for m in pattern.finditer(s):
        sign = (m.group("sign") or "").strip()
        curr = m.group("curr") if "curr" in m.groupdict() and m.group("curr") else ""
        whole_raw = m.group("whole") or ""
        whole = whole_raw.replace(" ", "").replace("\u00a0", "")
        frac = m.group("frac")
        try:
            value = float(whole)
        except ValueError:
            continue
        # свободный режим: отсеиваем телефоны, даты и время; настоящая сумма —
        # знак, валюта, десятичная дробь или пробел-разделитель между цифрами.
        # Отдельно: число, начинающее дату (26.06.2026), суммой не является
        if not strict and not (
            sign or curr or frac or re.search(r"\d[ \u00a0]\d", whole_raw)
        ):
            continue
        if not strict and re.match(
            r"\d{1,2}[./]\d{1,2}[./]\d{2,4}", s[m.start():].lstrip()
        ):
            continue
        v = value + (int(frac) / 10 ** len(frac) if frac else 0)
        # 10+ цифр — это номера счетов, коды авторизации и телефоны, не суммы
        if v >= 1_000_000_000 or len(whole) >= 10:
            continue
        out.append((sign, round(v, 2), m.start()))
    return out


def _parse_money(s: str, strict: bool) -> tuple[str, float | None]:
    """Возвращает (знак, сумма). Пример: '-599,00 ₽' → ('-', 599.0).

    Перебирает все совпадения: левое может оказаться фрагментом даты
    ('26.06' в '26.06.2026 ... 7 000,00'), отбраковывается защитой, и нужно
    взять следующее настоящее — сумму в конце строки.
    """
    matches = _money_matches(s, strict)
    if not matches:
        return "", None
    sign, value, _ = matches[0]
    return sign, value


_AUTH_CODE_RE = re.compile(r"^\d{4,8}\s*")
_OP_BY_CARD_RE = re.compile(r"\s*Операция по карте(?:\s*\*{2,}[\dx]+)?\s*$", re.IGNORECASE)


def _clean_desc(desc: str) -> str:
    """Убирает служебный хвост «Операция по карте ****0490», даты и мусор."""
    desc = _OP_BY_CARD_RE.sub("", desc)
    desc = _DATE_RE.sub(" ", desc)
    return re.sub(r"\s+", " ", desc).strip(" -–−.")


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

    Поддерживает форматы:
      1) многострочный (Сбер):  '05.08.26 17:04' / '−599,00 ₽' / 'NETFLIX.COM ...'
      2) однострочный:          '05.08.2026  NETFLIX.COM  -599,00 ₽'
      3) дебетовая карта Сбера: списания без знака, пополнения с '+', описание
         операции идёт следующей строкой (дата + код авторизации + текст)
    """
    has_currency = any(("₽" in l or "руб" in l or "RUB" in l) for l in lines)
    # строгий режим — только когда в выписке реально есть знак минус в сумме.

    # беззнаковые суммы (напр. "599.0 RUB") парсятся свободным режимом,
    # чтобы тестовые PDF-выписки не теряли транзакции вообще.
    strict = has_currency and any(
        (s := _parse_money(l, True)[0]) and s in "−–-"
        for l in lines if not _PDF_SKIP_RE.search(l)
    )

    signs = [_parse_money(l, strict)[0] for l in lines]
    saw_minus = any(s and s in "−–-" for s in signs)
    has_plus = any(s == "+" for s in signs)

    # Правило отбора: минус — точно списание; если в выписке плюсы есть,
    # а минусов нет (дебетовая карта Сбера), беззнаковые суммы — списания,
    # а с плюсом — пополнения, их не учитываем.
    if saw_minus:
        def _keep(s: str) -> bool:
            return s in "−–-"
    elif has_plus:
        def _keep(s: str) -> bool:
            return s != "+"
    else:
        def _keep(s: str) -> bool:
            return True

    _AUTH_CODE_RE = re.compile(r"^\d{4,8}\b\s*")
    _OP_BY_CARD_RE = re.compile(r"Операция по карте [*x\d]+\s*$", re.IGNORECASE)

    txs: list[dict] = []
    pending: dict | None = None  # {'date': date, 'amount': float|None, 'desc': [str]}
    last_was_simple = False  # предыдущая строка добавила транзакцию сама (однострочный формат)

    def flush() -> None:
        nonlocal pending
        if pending and pending["amount"]:
            desc = re.sub(r"\s+", " ", " ".join(pending["desc"])).strip(" -–−.")
            desc = _DATE_RE.sub(" ", desc)
            desc = _TIME_IN_DESC_RE.sub(" ", desc)
            desc = _clean_desc(re.sub(r"\s+", " ", desc))
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
        matches = _money_matches(line, strict)
        sign, amount = (matches[0][0], matches[0][1]) if matches else ("", None)
        is_skip = bool(_PDF_SKIP_RE.search(line))
        has_money = bool(matches)

        if m_date and has_money:
            # однострочный формат: дата + (описание) + [сумма + остаток]
            if is_skip:
                continue
            flush()
            d = _parse_date(m_date.group(1))
            if not d:
                continue
            # в конце строки два числа: предпоследнее — сумма, последнее — остаток
            sign, amount, m_start = matches[-2] if len(matches) >= 2 else matches[0]
            desc = (line[:m_date.start()] + " " + line[m_date.end():m_start])
            desc = _TIME_IN_DESC_RE.sub(" ", desc)
            desc = _clean_desc(re.sub(r"\s+", " ", desc))
            keep = _keep(sign)
            if desc and not _TIME_ONLY_RE.fullmatch(desc):
                if amount and keep:
                    txs.append({"date": d, "amount": amount, "description": desc[:120]})
                    last_was_simple = True
                else:
                    last_was_simple = False  # кредитная строка — не приклеивать описание
            else:
                # дата + сумма, описание пойдёт следующими строками
                start_tx(d, amount if (keep and amount) else None)
                last_was_simple = False
            continue

        if m_date:
            # строка с датой без суммы. Два сценария склейки:
            #   a) описание предыдущей однострочной операции (дата + код + текст);
            #   b) продолжение pending, у которого уже есть сумма, но нет описания
            #      (дата + категория + сумма, описание следующей строкой).
            rest = line[m_date.end():].strip()
            rest_clean = _clean_desc(_AUTH_CODE_RE.sub("", rest, count=1))

            # ВАЖНО: здесь не проверяем is_skip — в этом формате каждая строка
            # описания содержит «Операция по карте», а skip-слова («операци»)
            # предназначены только для отсева шапок при создании новой транзакции
            if txs and last_was_simple and pending is None and rest_clean:
                txs[-1]["description"] = rest_clean[:120]
                last_was_simple = False
                continue
            if pending is not None and pending["amount"] is not None and not pending["desc"]:
                if rest_clean:
                    pending["desc"].append(rest_clean)
                last_was_simple = False
                continue

            # иначе — новая транзакция начинается (дата/время на отдельной строке)
            flush()
            last_was_simple = False
            d = _parse_date(m_date.group(1))
            if d and not is_skip:
                start_tx(d, None, rest if not _TIME_ONLY_RE.fullmatch(rest) else "")
            continue

        if has_money:
            # строка суммы текущей транзакции (или итог/баланс внизу)
            if pending is not None and not is_skip:
                pending["amount"] = amount if (_keep(sign) and amount) else None
            last_was_simple = False
            continue

        # обычная строка: продолжение описания или шапка/шум
        if pending is not None and not is_skip and not _TIME_ONLY_RE.fullmatch(line):
            pending["desc"].append(line)
        last_was_simple = False

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
    """Ключ группы: известный бренд либо нормализованное имя.
    Пустая нормализация (описание из одних цифр) не склеивает разные
    транзакции — ключом становится сырая строка."""
    canon = canonical_name(desc)
    if canon:
        return ("brand", canon[0])
    norm = normalize_description(desc)
    if not norm:
        norm = "raw:" + str(desc).strip().lower()
    return ("norm", norm)


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
    # микросписания (< 1 ₽) и нули — обрывки реквизитов, не операции
    txs = [t for t in txs if abs(t["amount"]) >= 1]
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
        # внутренние переводы и вклады — не подписки, даже при регулярности
        if _INTERNAL_RE.search(str(key[1])):
            continue
        # платежи ЖКХ и бюджетных учреждений — регулярные, но не подписки
        if _UTILITY_RE.search(str(key[1])):
            continue
        # покупки в рознице и по QR — не подписки, даже если повторяются
        if _RETAIL_RE.search(str(key[1])):
            continue
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
        # имя-обрывок («Qr») — не подписка
        if len(name.strip()) < 3:
            continue
        # следующее списание: дата в будущем даже если платежи давно прекратились
        next_date = _add_months(last, 1 if period == "monthly" else 12)
        while next_date < date.today():
            next_date = _add_months(next_date, 1 if period == "monthly" else 12)
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
            "next_charge": next_date.isoformat(),
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


def monthly_expense_series_from_txs(txs: list[dict], subs: list[dict], months: int = 6) -> list[dict]:
    """Расходы на подписки по месяцам из ФАКТИЧЕСКИХ списаний.

    В отличие от monthly_expense_series (ровная модель регулярных платежей),
    здесь видны пропуски месяцев и смены цены — график живой, как в выписке.
    """
    today = date.today()
    merchants: dict[str, dict] = {}
    for s in subs:
        for m in s.get("merchants", []):
            merchants[m] = s
    series = []
    for i in range(months - 1, -1, -1):
        d = _add_months(today.replace(day=1), -i)
        total = 0.0
        for t in txs:
            sub = merchants.get(t["description"])
            if sub is None:
                continue
            if t["date"].year == d.year and t["date"].month == d.month:
                total += abs(t["amount"])
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
