const BASE = "";

export async function fetchSubscriptions() {
  const res = await fetch(`${BASE}/api/subscriptions`);
  if (!res.ok) throw new Error("Не удалось получить данные");
  return res.json();
}

export async function uploadStatement(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/api/upload`, { method: "POST", body: form });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Ошибка загрузки файла");
  return data;
}

export async function resetToDemo() {
  await fetch(`${BASE}/api/reset`, { method: "POST" });
}

export async function generateLetter(sub) {
  const res = await fetch(`${BASE}/api/generate-letter`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: sub.name, amount: sub.amount, period: sub.period }),
  });
  if (!res.ok) throw new Error("Не удалось сгенерировать письмо");
  return res.json();
}

/**
 * Генерирует тестовую выписку и возвращает её превью (CSV текст + PDF-URL).
 */
export async function fetchTestPreview() {
  const res = await fetch(`${BASE}/api/generate-test-json`);
  if (!res.ok) throw new Error("Не удалось сгенерировать тестовую выписку");
  const data = await res.json();
  return { csv: data.csv_text, pdfUrl: base64ToPdfUrl(data.pdf_base64) };
}

/**
 * Загружает CSV-выписку на сервер для сканирования и возвращает результат анализа.
 * Используется при «Отправить на скан» — заново сканирует с сервера.
 */
export async function uploadTestToScan(csvText) {
  const form = new FormData();
  const file = new File([new Blob([csvText], { type: "text/csv" })], "test_statement.csv", { type: "text/csv" });
  form.append("file", file);
  const res = await fetch(`${BASE}/api/upload`, { method: "POST", body: form });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Ошибка загрузки тестовой выписки");
  return data;
}

function base64ToPdfUrl(b64) {
  const byteChars = atob(b64);
  const bytes = new Uint8Array(byteChars.length);
  for (let i = 0; i < byteChars.length; i++) bytes[i] = byteChars.charCodeAt(i);
  return URL.createObjectURL(new Blob([bytes], { type: "application/pdf" }));
}
