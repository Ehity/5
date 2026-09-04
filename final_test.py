import urllib.request, json

BASE = "http://127.0.0.1:8000"

def get_json(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

def post_file(url, file_content, filename="test.csv"):
    boundary = "----FormBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: text/csv\r\n\r\n"
    ).encode() + file_content + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(url, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

print("1. /api/generate-test...")
with urllib.request.urlopen(f"{BASE}/api/generate-test", timeout=10) as r:
    csv_data = r.read()
    newline = b"\n"
    print(f"   {len(csv_data)} bytes, {csv_data.count(newline)} lines")

print("\n2. POST /api/upload...")
res = post_file(f"{BASE}/api/upload", csv_data)
print(f"   mock: {res.get('mock')}")
print(f"   subs: {len(res.get('subscriptions', []))}")
print(f"   msg: {res.get('message')}")

print("\n3. GET /api/subscriptions...")
subs = get_json(f"{BASE}/api/subscriptions")
print(f"   mock: {subs.get('mock')}")
print(f"   subs: {len(subs.get('subscriptions', []))}")
print(f"   msg: {subs.get('message')}")