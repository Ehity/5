path = r"c:\Python\subscription-web\backend\analyzer.py"
content = open(path, encoding="utf-8").read()
old = '        stable = [i for i in items if abs(i["amount"] - median) <= median * 0.15]'
new = '        stable = [i for i in items if abs(i["amount"] - median) <= abs(median) * 0.15]'
if old in content:
    content = content.replace(old, new, 1)
    open(path, "w", encoding="utf-8").write(content)
    print("Fixed!")
else:
    print("Not found")
