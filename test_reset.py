import requests
BASE = "http://127.0.0.1:8000"
# Test reset
r = requests.post(f"{BASE}/api/reset")
print("Reset:", r.json())
# Check state after reset
r = requests.get(f"{BASE}/api/subscriptions")
data = r.json()
print(f"After reset: mock={data['mock']}, subs={len(data['subscriptions'])}, monthly={len(data['monthly'])}")
print(f"Message: {data['message']}")
