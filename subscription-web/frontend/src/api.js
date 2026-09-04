import {
  buildLetter, detectSubscriptions, monthlyExpenseSeries,
  monthlyExpenseSeriesAll, parseCsvText, testStatementCsv,
} from "./lib/analyzer.js";

const BASE = "";
// "server" — есть backend (start_web.bat); "static" — анализ в браузере (GitHub Pages).
let mode = null;

async function detectMode() {
  if (mode) return mode;
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 1500);
    const res = await fetch(`${BASE}/api/health`, { signal: ctrl.signal });
    clearTimeout(timer);
    mode = res.ok ? "server" : "static";
  } catch {
    mode = "static";
  }
  return mode;
}

async function analyzeInBrowser(text) {
  const txs = parseCsvText(text);
  const subs = detectSubscriptions(txs);
  if (!subs.length) {
    return {
      mock: false,
      subscriptions: [],
      monthly: monthlyExpenseSeriesAll(txs),
      total_monthly: 0,
      total_yearly: 0,
      message: `В выписке (${txs.length} транзакций) не найдено регулярных списаний — показаны общие расходы по выписке`,
    };
  }
  return {
    mock: false,
    subscriptions: subs,
    monthly: monthlyExpenseSeries(subs),
    total_monthly: +subs.reduce((acc, s) => acc + Math.abs(s.monthly_cost), 0).toFixed(2),
    total_yearly: +subs.reduce((acc, s) => acc + Math.abs(s.yearly_cost), 0).toFixed(2),
    message: `Выписка: ${txs.length} транзакций, найдено подписок: ${subs.length}`,
  };
}

function emptyState() {
  return {
    mock: false,
    subscriptions: [],
    monthly: [],
    total_monthly: 0,
    total_yearly: 0,
    message: "Загрузите выписку, чтобы увидеть найденные подписки",
  };
}

export async function fetchSubscriptions() {
  if ((await detectMode()) === "static") {
    const saved = sessionStorage.getItem("scannerState");
    return saved ? JSON.parse(saved) : emptyState();
  }
  const res = await fetch(`${BASE}/api/subscriptions`);
  if (!res.ok) throw new Error("Не удалось получить данные");
  return res.json();
}

async function readFileText(file) {
  const buf = await file.arrayBuffer();
  for (const enc of ["utf-8", "windows-1251"]) {
    try {
      const text = new TextDecoder(enc, { fatal: true }).decode(buf);
      if (!text.includes("\uFFFD")) return text;
    } catch { /* попробуем следующую кодировку */ }
  }
  return new TextDecoder("windows-1251").decode(buf);
}

export async function uploadStatement(file) {
  if ((await detectMode()) === "server") {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${BASE}/api/upload`, { method: "POST", body: form });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Ошибка загрузки файла");
    return data;
  }
  // Браузерный режим: CSV/TXT анализируем на месте, PDF — только на сервере.
  const fname = (file.name || "").toLowerCase();
  if (fname.endsWith(".pdf")) {
    throw new Error("PDF поддерживается серверной версией (start_web.bat). В браузерном режиме загрузите CSV-выписку.");
  }
  if (!fname.endsWith(".csv") && !fname.endsWith(".txt")) {
    throw new Error("Поддерживаются форматы CSV и PDF (выписка СберБанк Онлайн)");
  }
  const text = await readFileText(file);
  let result;
  try {
    result = await analyzeInBrowser(text);
  } catch (e) {
    throw new Error(e.message || "Не удалось разобрать файл");
  }
  sessionStorage.setItem("scannerState", JSON.stringify(result));
  return result;
}

export async function resetToDemo() {
  if ((await detectMode()) === "server") {
    await fetch(`${BASE}/api/reset`, { method: "POST" });
  } else {
    sessionStorage.removeItem("scannerState");
  }
}

export async function generateLetter(sub) {
  if ((await detectMode()) === "server") {
    const res = await fetch(`${BASE}/api/generate-letter`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: sub.name, amount: sub.amount, period: sub.period }),
    });
    if (!res.ok) throw new Error("Не удалось сгенерировать письмо");
    return res.json();
  }
  return { letter: buildLetter({ name: sub.name, amount: sub.amount }) };
}

/** Тестовая выписка для превью (в браузерном режиме — без PDF). */
export async function fetchTestPreview() {
  if ((await detectMode()) === "server") {
    const res = await fetch(`${BASE}/api/generate-test-json`);
    if (!res.ok) throw new Error("Не удалось сгенерировать тестовую выписку");
    const data = await res.json();
    return { csv: data.csv_text, pdfUrl: base64ToPdfUrl(data.pdf_base64) };
  }
  return { csv: testStatementCsv(), pdfUrl: null };
}

/** Загружает тестовую выписку на скан (в браузерном режиме — анализ на месте). */
export async function uploadTestToScan(csvText) {
  if ((await detectMode()) === "server") {
    const form = new FormData();
    const file = new File([new Blob([csvText], { type: "text/csv" })], "test_statement.csv", { type: "text/csv" });
    form.append("file", file);
    const res = await fetch(`${BASE}/api/upload`, { method: "POST", body: form });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Ошибка загрузки тестовой выписки");
    return data;
  }
  const result = await analyzeInBrowser(csvText);
  sessionStorage.setItem("scannerState", JSON.stringify(result));
  return result;
}

function base64ToPdfUrl(b64) {
  const byteChars = atob(b64);
  const bytes = new Uint8Array(byteChars.length);
  for (let i = 0; i < byteChars.length; i++) bytes[i] = byteChars.charCodeAt(i);
  return URL.createObjectURL(new Blob([bytes], { type: "application/pdf" }));
}
