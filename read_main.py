with open(r"c:\Python\subscription-web\backend\main.py", "r") as f:
    lines = f.readlines()
for i, line in enumerate(lines[68:130], start=69):
    print(f"{i}: {line}", end="")