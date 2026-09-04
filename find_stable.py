path = r"c:\Python\subscription-web\backend\analyzer.py"
content = open(path, encoding="utf-8").read()
for i, line in enumerate(content.splitlines()):
    if "median * 0.15" in line:
        print(f"Line {i+1}: {repr(line)}")
