import io
import random
from datetime import date, timedelta

# Random test statement: subscriptions with noisy names + noise. In memory only.
# (base_amount, day_of_month, variants separated by pipe)
SERVICES = [
    (599.0, 5, 'NETFLIX.COM 866-579-7172 US|NFLX* 8NQ4R2|Netflix'),
    (399.0, 7, 'YNDX_PLUS|YNDX.MUSIC|ЯНДЕКС.ПЛЮС'),
    (299.0, 12, 'IVI.RU|IVI* 8NQ4R2|Иви'),
    (449.0, 3, 'OKKO.SUBSCRIPTION|Okko|OKKO.TV'),
    (169.0, 1, 'TG_PREMIUM|Telegram Premium|PremiumBot'),
    (299.0, 10, 'VK.COM|SUBSCRIPTION VK|VK Музыка'),
    (249.0, 15, 'KION.RU|KION Subscription|КИОН'),
    (399.0, 5, 'KINOPOISK HD|Кинопоиск|KP*HD'),
]

# Случайные шумовые транзакции (не подписки) — одноразовые покупки
NOISE = [
    ('PYATEROCHKA 2451', lambda r: round(random.uniform(150, 1500), 2)),
    ('MAGAZIN MAGNIT', lambda r: round(random.uniform(200, 3000), 2)),
    ('STARBUCKS COFFEE', lambda r: round(random.uniform(150, 800), 2)),
    ('YANDEX TAXI', lambda r: round(random.uniform(150, 1200), 2)),
    ('APTEKA 36.6', lambda r: round(random.uniform(100, 1500), 2)),
    ('MCDONALDS', lambda r: round(random.uniform(200, 900), 2)),
    ('KFC', lambda r: round(random.uniform(250, 1000), 2)),
    ('AZS LUKOIL', lambda r: round(random.uniform(800, 3000), 2)),
    ('CINEMA PARK', lambda r: round(random.uniform(400, 1800), 2)),
    ('OZON WILDBERRIES', lambda r: round(random.uniform(500, 5000), 2)),
]


def _random_day(d: date) -> date:
    """Возвращает дату в диапазоне [today-120d, today] с весом в сторону недавних."""
    delta = random.randint(0, 120)
    return d - timedelta(days=delta)


def generate_test_csv() -> bytes:
    """Генерирует CSV-выписку за 4 месяца без подписок (только шум)."""
    today = date.today()
    rng = random.Random(42)  # детерминированность для демо
    random.seed(42)

    lines = ["Date,Description,Amount,Category"]
    rows = []
    # 4 месяца шумовых транзакций
    for _ in range(40):
        d = _random_day(today)
        desc, fn = rng.choice(NOISE)
        amt = -abs(fn(rng))
        rows.append((d, desc, amt, "Прочее"))

    # Сортируем по дате
    rows.sort(key=lambda r: r[0])
    for d, desc, amt, cat in rows:
        lines.append(f"{d.isoformat()},{desc},{amt:.2f},{cat}")

    return ("\n".join(lines) + "\n").encode("utf-8")


def generate_test_pdf() -> bytes:
    """Генерирует простой PDF-выписку (без подписок) для предпросмотра."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # Заголовок
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Test Bank Statement")

    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, f"Statement period: {date.today() - timedelta(days=120)} — {date.today()}")
    c.drawString(50, height - 85, "Demo statement for Empty State demo — no subscriptions detected")

    # Заголовок таблицы
    c.setFont("Helvetica-Bold", 11)
    y = height - 120
    c.drawString(50, y, "Date")
    c.drawString(150, y, "Description")
    c.drawString(400, y, "Amount")

    # Содержимое — те же noise-транзакции
    c.setFont("Helvetica", 10)
    csv_data = generate_test_csv().decode("utf-8")
    reader = csv_data.split("\n")[1:]  # пропускаем заголовок
    random.seed(42)
    y -= 20
    for line in reader:
        if not line or y < 50:
            break
        parts = line.split(",")
        if len(parts) < 4:
            continue
        d, desc, amt, cat = parts
        c.drawString(50, y, d)
        c.drawString(150, y, desc[:40])
        c.drawString(400, y, f"{amt} RUB")
        y -= 16

    c.showPage()
    c.save()
    return buf.getvalue()
