import sys
sys.path.insert(0, r"c:\Python\subscription-web\backend")
from analyzer import canonical_name, detect_subscriptions, parse_csv

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
print("Transactions:")
for t in txs:
    print(f"  {t['date']} {t['amount']} {t['description']}")

groups = {}
for t in txs:
    canon = canonical_name(t["description"])
    key = ("brand", canon[0]) if canon else ("norm", "other")
    groups.setdefault(key, []).append(t)

print("\nGroups:")
for key, items in groups.items():
    dates = sorted([i["date"] for i in items])
    amounts = sorted([i["amount"] for i in items])
    median = amounts[len(amounts)//2]
    stable = [i for i in items if abs(i["amount"]-median) <= median*0.15]
    print(f"  {key}: {len(items)} items, dates={dates}")
    print(f"    amounts={amounts}, median={median}, stable={len(stable)}")
    if len(stable) >= 3:
        stable.sort(key=lambda t: t["date"])
        gaps = sorted([(stable[i+1]["date"]-stable[i]["date"]).days for i in range(len(stable)-1)])
        print(f"    gaps={gaps}")
        gaps2 = [g for g in gaps if g >= 10]
        print(f"    gaps>=10: {gaps2}")
        if gaps2:
            med_gap = gaps2[len(gaps2)//2]
            print(f"    med_gap={med_gap}, in [20,40]={20<=med_gap<=40}")
