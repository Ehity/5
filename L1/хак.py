from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import random
from datetime import date, timedelta

# Настройки документа
doc = SimpleDocTemplate("vybiska_podpisok.pdf", pagesize=A4)
styles = getSampleStyleSheet()
elements = []

# Заголовок
title = Paragraph("ВЫПИСКА О РАСХОДАХ", styles['Title'])
elements.append(title)
elements.append(Paragraph("Ежемесячные подписки и регулярные платежи", styles['Normal']))
elements.append(Spacer(1, 12))

# Период
period = Paragraph(f"Период: {date.today().replace(day=1) - timedelta(days=90)} — {date.today()}", styles['Normal'])
elements.append(period)
elements.append(Spacer(1, 12))

# Список подписок с примерными ценами (руб.)
subscriptions = [
    ("Netflix", 799), ("Spotify Premium", 169), ("YouTube Premium", 199),
    ("Apple Music", 169), ("Amazon Prime Video", 299), ("Adobe Creative Cloud", 1550),
    ("Microsoft 365", 699), ("Google One 200GB", 269), ("Disney+", 699),
    ("HBO Max", 399), ("Яндекс Плюс", 299), ("Кинопоиск HD", 399),
    ("IVI", 399), ("Okko", 299), ("More.tv", 299), ("СберПрайм", 399),
    ("Telegram Premium", 299), ("Discord Nitro", 599), ("Xbox Game Pass", 999),
    ("PlayStation Plus", 849), ("Nintendo Switch Online", 249), ("VPN-сервис", 199),
    ("Облачное хранилище Dropbox", 1199), ("LastPass Premium", 299),
    ("Антивирус Kaspersky", 450), ("Антивирус Dr.Web", 390),
    ("1С:Облако", 750), ("Figma Professional", 1200), ("Notion Plus", 400)
]

# Генерация записей за последние 3 месяца
data = [["Дата", "Название подписки", "Категория", "Сумма, руб."]]
total_sum = 0
current_date = date.today()

for month_offset in range(3):
    # Определяем первый день месяца (для разнообразия дат)
    month_start = (current_date.replace(day=1) - timedelta(days=month_offset * 30)).replace(day=1)
    # Для каждого месяца генерируем от 5 до 12 случайных подписок с разными датами
    num_records = random.randint(5, 12)
    used_indices = random.sample(range(len(subscriptions)), num_records)
    for idx in used_indices:
        sub_name, price = subscriptions[idx]
        # Случайная дата в пределах месяца (от 1 до 28 числа, чтобы избежать проблем с февралём)
        day = random.randint(1, 28)
        record_date = month_start.replace(day=day)
        # Небольшое случайное изменение цены ±10%
        price_variation = random.uniform(-0.1, 0.1)
        actual_price = round(price * (1 + price_variation), 2)
        category = "Развлечения" if any(s in sub_name for s in ["Netflix", "Spotify", "YouTube", "Apple Music", "Amazon Prime", "Disney", "HBO", "Кинопоиск", "IVI", "Okko", "More.tv", "СберПрайм"]) else \
                   "Программы и сервисы" if any(s in sub_name for s in ["Adobe", "Microsoft", "Google", "Dropbox", "LastPass", "Антивирус", "1С", "Figma", "Notion", "Telegram", "Discord", "VPN"]) else \
                   "Игры"
        data.append([record_date.strftime("%d.%m.%Y"), sub_name, category, f"{actual_price:.2f}"])
        total_sum += actual_price

# Итоговая строка
data.append(["", "", "ИТОГО:", f"{total_sum:.2f}"])

# Создание таблицы
table = Table(data, colWidths=[30*mm, 60*mm, 50*mm, 30*mm])
table.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.grey),
    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
    ('ALIGN', (0,0), (-1,0), 'CENTER'),
    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ('FONTSIZE', (0,0), (-1,0), 10),
    ('BOTTOMPADDING', (0,0), (-1,0), 12),
    ('BACKGROUND', (0,1), (-1,-1), colors.beige),
    ('GRID', (0,0), (-1,-1), 1, colors.black),
    ('ALIGN', (3,1), (3,-1), 'RIGHT'),
    ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
    ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
    ('SPAN', (0,-1), (2,-1)),  # Объединить ячейки для "ИТОГО"
]))

elements.append(table)
doc.build(elements)
print("PDF успешно создан: vybiska_podpisok.pdf")