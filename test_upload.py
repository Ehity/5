import urllib.request, json

BASE = "http://127.0.0.1:8000"

# Step 1: Fetch test CSV
with urllib.request.urlopen(f"{BASE}/api/generate-test", timeout=10) as r:
    csv_data = r.read()
print(f"CSV: {len(csv_data)} bytes")

# Step 2: Upload it
boundary = "----FormBoundary"
body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="test.csv"\r\n'
    f"Content-Type: text/csv\r\n\r\n"
).encode() + csv_data + f"\r\n--{boundary}--\r\n".encode()

req = urllib.request.Request(
    f"{BASE}/api/upload", data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    method="POST"
)

try:
    with urllib.request.urlopen(req, timeout=15) as r:
        result = json.loads(r.read())
        print("UPLOAD OK:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"UPLOAD ERROR: {type(e).__name__}: {e}")
    if hasattr(e, 'read'):
        print("Response:", e.read().decode()[:500])

# Step 3: Check subscriptions
print("\nSubscriptions after upload:")
with urllib.request.urlopen(f"{BASE}/api/subscriptions", timeout=10) as r:
    result = json.loads(r.read())
    print(json.dumps(result, indent=2, ensure_ascii=False))