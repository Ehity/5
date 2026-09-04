import sys
sys.path.insert(0, r"c:\Python\subscription-web\backend")
import csv
import io

# Test CSV data (like what generate_test_csv produces)
csv_text = """Date,Description,Amount,Category
2026-05-08,MAGAZIN MAGNIT,-2113.93,Прочее
2026-05-09,KFC,-533.90,Прочее
2026-05-13,YANDEX TAXI,-722.63,Прочее"""

content = csv_text.encode("utf-8")

# Test 1: encoding detection
for enc in ("utf-8-sig", "utf-8", "cp1251"):
    try:
        text = content.decode(enc)
        print(f"Encoding {enc}: OK, first 50 chars: {text[:50]}")
        break
    except UnicodeDecodeError:
        print(f"Encoding {enc}: FAILED")

# Test 2: sniff delimiter
sample = text[:4096]
try:
    dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
    print(f"Sniffer detected delimiter: '{dialect.delimiter}'")
except csv.Error as e:
    print(f"Sniffer error: {e}, using excel dialect (delimiter=';')")
    dialect = csv.excel

# Test 3: parse
reader = csv.DictReader(io.StringIO(text), dialect=dialect)
headers = reader.fieldnames
print(f"Headers: {headers}")

rows = list(reader)
print(f"Parsed rows: {len(rows)}")
for row in rows[:3]:
    print(f"  Row: {row}")
