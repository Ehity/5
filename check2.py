import sys
sys.path.insert(0, r"c:\Python\subscription-web\backend")
from analyzer import canonical_name, detect_subscriptions, parse_csv

tests = ["NETFLIX.COM", "YANDEX_PLUS", "IVI", "KINOPOISK"]
for t in tests:
    result = canonical_name(t)
    name = result[0] if result else None
    print(repr(t), "->", name)

csv_data = "Date,Description,Amount,Category\n"
csv_data += "2026-09-01,NETFLIX.COM,-599.00,Podpiski\n"
csv_data += "2026-09-01,YANDEX_PLUS,-299.00,Podpiski\n"
csv_data += "2026-08-01,NETFLIX.COM,-599.00,Podpiski\n"
csv_data += "2026-08-01,YANDEX_PLUS,-299.00,Podpiski\n"
csv_data += "2026-07-01,NETFLIX.COM,-599.00,Podpiski\n"
csv_data += "2026-07-01,YANDEX_PLUS,-299.00,Podpiski\n"
csv_data += "2026-06-01,NETFLIX.COM,-599.00,Podpiski\n"
csv_data += "2026-06-01,YANDEX_PLUS,-299.00,Podpiski\n"

txs = parse_csv(csv_data.encode())
print("\nParsed:", len(txs), "txs")
subs = detect_subscriptions(txs)
print("Detected:", len(subs), "subs")
for s in subs:
    print("  -", s.get("name"), "| url:", s.get("cancel_url"))
