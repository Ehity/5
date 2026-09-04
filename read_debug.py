import sys
path = r"c:\Python\subscription-web\backend\main.py"
lines = open(path, encoding="utf-8").readlines()
for i in range(88, 96):
    print(f"{i+1}: {repr(lines[i])}")
