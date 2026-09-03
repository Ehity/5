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
