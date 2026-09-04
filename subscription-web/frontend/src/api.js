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
 * Генерирует тестовую CSV-выписку без подписок и загружает её на сервер.
 * Возвращает данные анализа (с пустыми подписками — Empty State).
 */
export async function generateTestStatement() {
  const res = await fetch(`${BASE}/api/generate-test`);
  if (!res.ok) throw new Error("Не удалось сгенерировать тестовую выписку");
  const blob = await res.blob();

  // Загружаем blob как файл на /api/upload
  const form = new FormData();
  const file = new File([blob], "test_statement.csv", { type: "text/csv" });
  form.append("file", file);
  const uploadRes = await fetch(`${BASE}/api/upload`, { method: "POST", body: form });
  const data = await uploadRes.json().catch(() => ({}));
  if (!uploadRes.ok) throw new Error(data.detail || "Ошибка загрузки тестовой выписки");
  return data;
}

/**
 * Возвращает Blob URL для PDF-превью тестовой выписки.
 */
export async function fetchTestPdfUrl() {
  const res = await fetch(`${BASE}/api/generate-test-pdf`);
  if (!res.ok) throw new Error("Не удалось получить PDF-выписку");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}
