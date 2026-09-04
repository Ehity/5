import sys
sys.path.insert(0, r"c:\Python\subscription-web\backend")
import urllib.request
import json

BASE = "http://127.0.0.1:8000"

# 1. Test health
try:
    with urllib.request.urlopen(f"{BASE}/api/health") as r:
        print("HEALTH:", r.read().decode())
except Exception as e:
    print("HEALTH ERROR:", e)

# 2. Test /api/subscriptions (should be empty state)
try:
    with urllib.request.urlopen(f"{BASE}/api/subscriptions") as r:
        data = json.loads(r.read())
        print("SUBSCRIPTIONS mock:", data.get("mock"))
        print("SUBSCRIPTIONS count:", len(data.get("subscriptions", [])))
        print("SUBSCRIPTIONS message:", data.get("message"))
except Exception as e:
    print("SUBSCRIPTIONS ERROR:", e)

# 3. Test /api/generate-test
try:
    with urllib.request.urlopen(f"{BASE}/api/generate-test") as r:
        csv_data = r.read()
        lines = csv_data.decode("utf-8").split("\n")
        print(f"GENERATE-TEST: {len(lines)} lines, first: {lines[0] if lines else 'EMPTY'}")
        print(f"GENERATE-TEST preview: {csv_data[:200]}")
except Exception as e:
    print("GENERATE-TEST ERROR:", e)

# 4. Test uploading generated CSV
try:
    # First get the CSV
    with urllib.request.urlopen(f"{BASE}/api/generate-test") as r:
        csv_data = r.read()
    
    # Upload it
    import urllib.parse
    boundary = "----FormBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="test.csv"\r\n'
        f"Content-Type: text/csv\r\n\r\n"
    ).encode() + csv_data + f"\r\n--{boundary}--\r\n".encode()
    
    req = urllib.request.Request(
        f"{BASE}/api/upload",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())
        print("UPLOAD RESULT mock:", result.get("mock"))
        print("UPLOAD RESULT subs count:", len(result.get("subscriptions", [])))
        print("UPLOAD RESULT message:", result.get("message"))
except Exception as e:
    print("UPLOAD ERROR:", e)
