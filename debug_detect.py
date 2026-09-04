import sys
sys.path.insert(0, r"c:\Python\subscription-web\backend")
from analyzer import canonical_name, detect_subscriptions, parse_csv, BRAND_RULES

print("BRAND_RULES for Yandex:")
for name, cat, icon, keys in BRAND_RULES:
    if "YNDX" in keys or "YANDEX" in keys:
        print(f"  {name}: keys={keys}")

# Test description matching
desc = "YANDEX_PLUS"
desc_upper = desc.upper()
print(f"\nTest: '{desc}' -> upper: '{desc_upper}'")
for name, cat, icon, keys in BRAND_RULES:
    if "YNDX" in keys or "YANDEX" in keys:
        for k in keys:
            found = k in desc_upper
            print(f"  '{k}' in '{desc_upper}' = {found}")

print("\ncanonical_name('YANDEX_PLUS'):", canonical_name("YANDEX_PLUS"))

# CSV with 4 months of data for Netflix + Yandex Plus
csv = "Date,Description,Amount,Category\n"
rows = [
    ("2026-09-01","NETFLIX.COM","-599.00"),
    ("2026-09-01","YANDEX_PLUS","-299.00"),
    ("2026-08-01","NETFLIX.COM","-599.00"),
    ("2026-08-01","YANDEX_PLUS","-299.00"),
    ("2026-07-01","NETFLIX.COM","-599.00"),
    ("2026-07-01","YANDEX_PLUS","-299.00"),
    ("2026-06-01","NETFLIX.COM","-599.00"),
    ("2026-06-01","YANDEX_PLUS","-299.00"),
]
for d, desc, amt in rows:
    csv += f"{d},{desc},{amt},Podpiski\n"

txs = parse_csv(csv.encode())
print(f"\nParsed: {len(txs)} transactions")
print("First tx:", txs[0])

# Debug grouping
from analyzer import normalize_description
groups = {}
for t in txs:
    canon = canonical_name(t["description"])
    key = ("brand", canon[0]) if canon else ("norm", normalize_description(t["description"]))
    groups.setdefault(key, []).append(t)

print("\nGroups:")
for key, items in groups.items():
    print(f"  {key}: {len(items)} items")
    for i in items:
        print(f"    {i['date']} {i['amount']} {i['description']}")
