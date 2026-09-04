import sys, csv, io, re
sys.path.insert(0, r"c:\Python\subscription-web\backend")
from analyzer import parse_csv, detect_subscriptions, COLUMN_ALIASES

csv_data = b"Date,Description,Amount,Category\n2026-05-08,MAGAZIN MAGNIT,-2113.93,Other\n2026-05-09,KFC,-533.90,Other\n2026-05-13,YANDEX TAXI,-722.63,Other"

print("Now running parse_csv:")
txs = parse_csv(csv_data)
print(f"parse_csv returned {len(txs)} transactions")
for t in txs:
    print(f"  {t}")

print()
print("Testing detect_subscriptions on noise-only CSV:")
subs = detect_subscriptions(txs)
print(f"Found {len(subs)} subscriptions (expected 0 for noise-only)")

print()
print("Testing WITH subscription transactions (NETFLIX):")
csv_with_sub = b"Date,Description,Amount,Category\n2026-05-01,NETFLIX.COM,-599.00,Other\n2026-06-01,NETFLIX.COM,-599.00,Other\n2026-07-01,NETFLIX.COM,-599.00,Other\n2026-08-01,NETFLIX.COM,-599.00,Other\n2026-05-08,MAGAZIN MAGNIT,-2113.93,Other"

txs2 = parse_csv(csv_with_sub)
print(f"Parsed {len(txs2)} transactions")
subs2 = detect_subscriptions(txs2)
print(f"Found {len(subs2)} subscriptions")
for s in subs2:
    print(f"  - {s['name']}: {s['monthly_cost']} rub/month, {s['charges']} charges")

