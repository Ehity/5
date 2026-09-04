"""Генерация PDF-выписки БЕЗ подписок (только шум) для теста fallback."""

from datetime import date, timedelta

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.platypus import Paragraph

OUT = r"c:\Python\subscription-web\test_no_subscriptions.pdf"

_ARIAL = r"C:\Windows\Fonts\arial.ttf"
try:
    pdfmetrics.registerFont(TTFont("ArialRu", _ARIAL))
    FONT_NAME = "ArialRu"
except Exception:
    FONT_NAME = "Helvetica"


def make_pdf(path):
    rows = []
    noise_names = [
        "ПЯТЕРОЧКА", "OZON.RU", "ЯНДЕКС ТАКСИ", "АЗС ЛУКОЙЛ",
        "WILDBERRIES", "АПТЕКА 36,6", "ВКУСВИЛЛ", "ПЕРЕКРЕСТОК",
    ]
    # 8 месяцев случайных покупок — никаких повторяющихся сумм
    noise_amounts = [340.0, 610.0, 990.0, 1480.0, 2070.0, 2510.0, 2980.0, 3340.0]
    for d_i in range(8):
        base = date(2026, 2 + d_i, 3)
        for j, name in enumerate(noise_names):
            am = noise_amounts[(j + d_i) % len(noise_amounts)]
            rows.append((base + timedelta(days=j * 2), "14:%02d" % j, name, am, "-"))
    rows.sort(key=lambda r: (r[0], r[1]))

    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title="Выписка по счёту 40817810000000012345",
    )
    styles = {
        "title": ParagraphStyle("title", fontName=FONT_NAME, fontSize=14,
                                textColor=colors.HexColor("#1a1a1a")),
        "small": ParagraphStyle("small", fontName=FONT_NAME, fontSize=8,
                                textColor=colors.HexColor("#555"), leading=11),
    }
    elems = [
        Paragraph("Выписка по счёту 40817810000000012345", styles["title"]),
        Spacer(1, 4),
        Paragraph("Период: 03.02.2026 — 03.09.2026 | Владелец: ИВАНОВ ИВАН ИВАНОВИЧ | Валюта: RUB",
                  styles["small"]),
        Spacer(1, 8),
    ]
    header = ["Дата", "Время", "Описание операции", "Сумма"]
    data = [header]
    for (dd, tm, desc, am, sign) in rows:
        data.append([dd.strftime("%d.%m.%Y"), tm, desc,
                     f"{sign}{am:,.2f} руб.".replace(",", " ")])

    table = Table(data, colWidths=[24 * mm, 18 * mm, 105 * mm, 35 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#21A038")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), FONT_NAME),
        ("FONTNAME", (0, 1), (-1, -1), FONT_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f4f4")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elems.append(table)
    doc.build(elems)
    print(f"PDF создан: {path} ({len(rows)} транзакций, без подписок)")


if __name__ == "__main__":
    make_pdf(OUT)