path = r"c:\Python\subscription-web\backend\analyzer.py"
content = open(path, encoding="utf-8").read()
old = '    ("Яндекс Плюс", "Развлечения", "🟡",\n     ["YNDX", "YANDEX PLUS", "ЯНДЕКС.ПЛЮС", "ЯНДЕКС ПЛЮС"]),'
new = '    ("Яндекс Плюс", "Развлечения", "🟡",\n     ["YNDX", "YANDEX PLUS", "YANDEX_PLUS", "ЯНДЕКС.ПЛЮС", "ЯНДЕКС ПЛЮС", "ЯНДЕКС+"]),'
if old in content:
    content = content.replace(old, new, 1)
    open(path, "w", encoding="utf-8").write(content)
    print("Added YANDEX_PLUS key to BRAND_RULES!")
else:
    print("Pattern not found!")
    # Try to find the current line
    for i, line in enumerate(content.splitlines()):
        if "YNDX" in line and "BRAND" not in line:
            print(f"Line {i+1}: {repr(line)}")
