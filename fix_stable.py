path = r"c:\Python\subscription-web\backend\analyzer.py"
content = open(path, encoding="utf-8").read()
old = "        if abs(i[\"amount\"] - median) <= median * 0.15:"
new = "        if abs(i[\"amount\"] - median) <= abs(median) * 0.15:"
if old in content:
    content = content.replace(old, new, 1)
    open(path, "w", encoding="utf-8").write(content)
    print("Fixed stable amount check!")
else:
    print("Pattern not found!")
