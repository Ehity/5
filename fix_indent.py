path = r"c:\Python\subscription-web\backend\main.py"
content = open(path, encoding="utf-8").read()
old = "        subs = detect_subscriptions(txs)\n"
new = "    subs = detect_subscriptions(txs)\n"
if old in content:
    content = content.replace(old, new, 1)
    open(path, "w", encoding="utf-8").write(content)
    print("Fixed! Indentation corrected.")
else:
    print("Pattern not found. Content around line 93:")
    lines = content.splitlines()
    for i in range(88, 98):
        print(f"{i+1}: {repr(lines[i])}")
