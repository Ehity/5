"""Генерирует icon.ico — иконку приложения (лупа + рубль на зелёном фоне Сбера)."""

from PIL import Image, ImageDraw, ImageFont

SIZE = 256
GREEN = (33, 160, 56, 255)       # фирменный зелёный Сбера
WHITE = (255, 255, 255, 255)
DARK = (14, 60, 26, 255)

img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# скруглённый зелёный фон
d.rounded_rectangle([8, 8, SIZE - 8, SIZE - 8], radius=52, fill=GREEN)

# лупа: кольцо
cx, cy, r = 112, 108, 62
for w, col in [(14, DARK), (12, WHITE)]:
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=w)
# ручка лупы
d.line([cx + r * 0.65, cy + r * 0.65, cx + 118, cy + 176], fill=WHITE, width=26)
d.line([cx + r * 0.65, cy + r * 0.65, cx + 118, cy + 176], fill=DARK, width=30)
d.line([cx + r * 0.65, cy + r * 0.65, cx + 118, cy + 176], fill=WHITE, width=22)

# символ рубля внутри линзы
try:
    font_big = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 84)
    d.text((cx, cy - 2), "\u20bd", font=font_big, fill=WHITE, anchor="mm")
except OSError:
    d.text((cx, cy), "P", font=ImageFont.load_default(), fill=WHITE, anchor="mm")

# символ повторяющегося платежа (циклические стрелки) в правом верхнем углу
arc_cx, arc_cy, arc_r = 196, 62, 30
d.arc([arc_cx - arc_r, arc_cy - arc_r, arc_cx + arc_r, arc_cy + arc_r],
      start=200, end=80, fill=WHITE, width=10)
d.arc([arc_cx - arc_r, arc_cy - arc_r, arc_cx + arc_r, arc_cy + arc_r],
      start=20, end=260, fill=WHITE, width=10)
# наконечники стрелок цикла (по часовой)
d.polygon([(arc_cx + 26, arc_cy - 24), (arc_cx + 12, arc_cy - 28), (arc_cx + 22, arc_cy - 8)],
          fill=WHITE)
d.polygon([(arc_cx - 26, arc_cy + 24), (arc_cx - 12, arc_cy + 28), (arc_cx - 22, arc_cy + 8)],
          fill=WHITE)

img.save(r"c:\Python\subscription-scanner\icon.ico",
         sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
img.save(r"c:\Python\subscription-scanner\icon.png")
print("icon.ico created")
