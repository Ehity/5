import requests
import io

BASE = "http://127.0.0.1:8000"
r = requests.get(f"{BASE}/api/generate-test")
csv_content = r.content
print(f"CSV size: {len(csv_content)} bytes")

# Try different file upload formats
files = {"file": ("test_statement.csv", io.BytesIO(csv_content), "text/csv")}
r = requests.post(f"{BASE}/api/upload", files=files)
print(f"Status: {r.status_code}")
print(f"Response: {r.text[:500]}")
