path = r"c:\Python\subscription-web\backend\analyzer.py"
content = open(path, encoding="utf-8").read()
old = '    ("Яндекс Плюс", "Развлечения", "🟡",\n     ["YNDX", "YANDEX PLUS", "YANDEX_PLUS", "ЯНДЕКС.ПЛЮС", "ЯНДЕКС ПЛЮС", "ЯНДЕКС+"]),'
new = '    ("Яндекс Плюс", "Развлечения", "🟡",\n     ["YNDX", "YANDEX_PLUS", "YANDEX PLUS", "ЯНДЕКС.ПЛЮС", "ЯНДЕКС ПЛЮС", "ЯНДЕКС+"]),'
if old in content:
    content = content.replace(old, new, 1)
    open(path, "w", encoding="utf-8").write(content)
    print("Fixed key order!")
else:
    print("Pattern not found")
    for i, line in enumerate(content.splitlines()):
        if "YANDEX" in line.upper() and "BRAND" not in line.upper():
            print(f"Line {i+1}: {repr(line)}")
