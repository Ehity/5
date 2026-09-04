import requests
import io

# 1. Проверить health
r = requests.get("http://127.0.0.1:8000/api/health")
print("Health:", r.json())

# 2. GET /api/subscriptions
r = requests.get("http://127.0.0.1:8000/api/subscriptions")
print("\nGET /api/subscriptions:", r.json())

# 3. Скачать тестовый CSV
r = requests.get("http://127.0.0.1:8000/api/generate-test")
csv_content = r.content
print(f"\nТестовый CSV: {len(csv_content)} байт")
print("Первые 200 символов:", csv_content[:200].decode("utf-8", errors="replace"))

# 4. Загрузить CSV на /api/upload
files = {"file": ("test_statement.csv", io.BytesIO(csv_content), "text/csv")}
r = requests.post("http://127.0.0.1:8000/api/upload", files=files)
print(f"\nPOST /api/upload: status={r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"  subscriptions: {len(data['subscriptions'])} шт.")
    print(f"  monthly: {data['monthly'][:3]}")
    print(f"  message: {data.get('message', '')}")
else:
    print(f"  Ошибка: {r.text}")
