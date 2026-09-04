import sys, requests, io
sys.path.insert(0, r"c:\Python\subscription-web\backend")
from analyzer import canonical_name, detect_subscriptions, parse_csv

# Test canonical_name with new keys
for t in ["NETFLIX.COM", "YANDEX_PLUS", "IVI", "KINOPOISK"]:
    r = canonical_name(t)
    print(repr(t), "->", r[0] if r else None)

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
print("\nParsed:", len(txs), "transactions")
subs = detect_subscriptions(txs)
print("Detected:", len(subs), "subscriptions")
for s in subs:
    print(f"  - {s.get('name')}: monthly={s.get('monthly_cost')} -> cancel_url={s.get('cancel_url', 'MISSING')}")

# Now test the FULL flow via API
BASE = "http://127.0.0.1:8000"
r = requests.post(f"{BASE}/api/upload", files={"file": ("subs.csv", csv.encode(), "text/csv")})
data = r.json()
print(f"\nAPI upload status: {r.status_code}")
print(f"API returned: {len(data['subscriptions'])} subscriptions")
for s in data.get("subscriptions", []):
    print(f"  - {s.get('name')}: cancel_url = {s.get('cancel_url', 'MISSING')}")
    print(f"    monthly: {s.get('monthly_cost')} руб, period: {s.get('period')}")
