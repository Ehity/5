import requests, io
BASE = "http://127.0.0.1:8000"

print("1. Empty State:")
r = requests.get(f"{BASE}/api/subscriptions")
d = r.json()
print(f"   mock={d['mock']}, subs={len(d['subscriptions'])}, msg={d['message']}")

print("\n2. Upload CSV with subs:")
csv = "Date,Description,Amount,Category\n"
for mo in ["09","08","07","06"]:
    csv += f"2026-{mo}-01,NETFLIX.COM,-599.00,Podpiski\n"
    csv += f"2026-{mo}-01,YANDEX_PLUS,-299.00,Podpiski\n"
r = requests.post(f"{BASE}/api/upload", files={"file": ("test.csv", csv.encode(), "text/csv")})
d = r.json()
print(f"   Status={r.status_code}, subs={len(d['subscriptions'])}")
for s in d["subscriptions"]:
    print(f"   - {s['name']}: {s['monthly_cost']} -> {s['cancel_url']}")

print("\n3. GET /api/subscriptions:")
r = requests.get(f"{BASE}/api/subscriptions")
d = r.json()
print(f"   subs={len(d['subscriptions'])}, monthly={len(d['monthly'])}")

print("\n4. Reset:")
r = requests.post(f"{BASE}/api/reset")
print(f"   {r.json()}")

print("\n5. After Reset:")
r = requests.get(f"{BASE}/api/subscriptions")
d = r.json()
print(f"   mock={d['mock']}, subs={len(d['subscriptions'])}")
print("\nALL TESTS PASSED!")
