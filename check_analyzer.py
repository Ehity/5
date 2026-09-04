import sys
sys.path.insert(0, r"c:\Python\subscription-web\backend")
from analyzer import canonical_name, detect_subscriptions

tests = ["NETFLIX.COM", "YANDEX_PLUS", "IVI", "ЯНДЕКС.ПЛЮС", "KINOPOISK"]
for t in tests:
    result = canonical_name(t)
    print(f"canonical_name('{t}') = {result}")

# Test CSV parsing
import io, csv
csv_data = "Date,Description,Amount,Category\n2026-09-01,NETFLIX.COM,-599.00,Podpiski\n2026-09-01,YANDEX_PLUS,-299.00,Podpiski\n2026-08-01,NETFLIX.COM,-599.00,Podpiski\n2026-08-01,YANDEX_PLUS,-299.00,Podpiski\n2026-07-01,NETFLIX.COM,-599.00,Podpiski\n2026-07-01,YANDEX_PLUS,-299.00,Podpiski\n2026-06-01,NETFLIX.COM,-599.00,Podpiski\n2026-06-01,YANDEX_PLUS,-299.00,Podpiski\n"
from analyzer import parse_csv
txs = parse_csv(csv_data.encode())
print(f"\nParsed transactions: {len(txs)}")
for t in txs[:4]:
    print(f"  {t}")
subs = detect_subscriptions(txs)
print(f"\nDetected subscriptions: {len(subs)}")
for s in subs:
    print(f"  - {s}")
