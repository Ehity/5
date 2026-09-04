with open(r"c:\Python\subscription-web\backend\uvicorn.log", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()
print(f"Total lines: {len(lines)}")
for line in lines[-10:]:
    print(line.rstrip())
