import requests, io

BASE = "http://127.0.0.1:8000"
# CSV с подписками
csv = b"""Date,Description,Amount,Category
2026-09-01,NETFLIX.COM,-599.00,Подписки
2026-09-01,YANDEX_PLUS,-299.00,Подписки
2026-09-01,IVI,-299.00,Подписки
2026-08-01,NETFLIX.COM,-599.00,Подписки
2026-08-01,YANDEX_PLUS,-299.00,Подписки
"""
r = requests.post(f"{BASE}/api/upload", files={"file": ("subs.csv", io.BytesIO(csv), "text/csv")})
data = r.json()
print(f"Status: {r.status_code}")
print(f"Subs found: {len(data['subscriptions'])}")
for s in data["subscriptions"]:
    print(f"  - {s['name']}: {s.get('cancel_url', 'NO URL')}")
print(f"monthly: {data['monthly'][:2]}")
