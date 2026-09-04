import requests, io
BASE = "http://127.0.0.1:8000"
csv = "Date,Description,Amount,Category\n"
csv += "2026-09-01,NETFLIX.COM,-599.00,Podpiski\n"
csv += "2026-09-01,YANDEX_PLUS,-299.00,Podpiski\n"
csv += "2026-09-01,IVI,-299.00,Podpiski\n"
csv += "2026-08-01,NETFLIX.COM,-599.00,Podpiski\n"
csv += "2026-08-01,YANDEX_PLUS,-299.00,Podpiski\n"
r = requests.post(f"{BASE}/api/upload", files={"file": ("subs.csv", io.BytesIO(csv.encode()), "text/csv")})
data = r.json()
print(f"Status: {r.status_code}")
print(f"Subs found: {len(data['subscriptions'])}")
for s in data["subscriptions"]:
    print(f"  - {s.get('name','?')}: {s.get('cancel_url', 'NO URL')}")
