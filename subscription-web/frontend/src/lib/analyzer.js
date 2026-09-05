// Порт analyzer.py + services_db.py на JavaScript — позволяет работать
// полностью в браузере (GitHub Pages) без backend.

import { detectSubscriptionPriceChange } from "./subscriptionPriceChange.js";

// pdf.js грузим лениво: модуль анализатора остаётся пригодным для Node-тестов.
let _pdfjs = null;
async function getPdfjs() {
  if (!_pdfjs) {
    const [lib, { default: workerUrl }] = await Promise.all([
      import("pdfjs-dist/legacy/build/pdf.mjs"),
      import("pdfjs-dist/legacy/build/pdf.worker.min.mjs?url"),
    ]);
    lib.GlobalWorkerOptions.workerSrc = workerUrl;
    _pdfjs = lib;
  }
  return _pdfjs;
}

/** Извлекает строки текста из PDF-выписки (координатная сборка строк). */
export async function extractPdfLines(buf) {
  let pdf;
  try {
    const pdfjsLib = await getPdfjs();
    pdf = await pdfjsLib.getDocument({ data: buf }).promise;
  } catch (e) {
    console.error(e);
    throw new Error(
      "Не удалось обработать PDF в этом браузере. Попробуйте обновить iOS/браузер или загрузите CSV-выписку."
    );
  }
  const lines = [];
  for (let p = 1; p <= pdf.numPages; p++) {
    const page = await pdf.getPage(p);
    const content = await page.getTextContent();
    const items = content.items
      .filter((it) => it.str !== undefined)
      .map((it) => ({ str: it.str, x: it.transform[4], y: Math.round(it.transform[5]) }))
      .sort((a, b) => b.y - a.y || a.x - b.x);
    let lastY = null;
    let line = "";
    for (const it of items) {
      if (lastY !== null && Math.abs(it.y - lastY) > 2) {
        if (line.trim()) lines.push(line.trim());
        line = "";
      }
      if (line && !line.endsWith(" ") && it.str && !it.str.startsWith(" ")) line += " ";
      line += it.str;
      lastY = it.y;
    }
    if (line.trim()) lines.push(line.trim());
  }
  return lines.filter((l) => l.trim());
}

// ---------------------------------------------------------------------------
// Порт PDF-парсера из analyzer.py (_transactions_from_lines)
// ---------------------------------------------------------------------------
const PDF_SKIP_RE = /продолжение|страниц|сформирова|справк|выписк|сч[её]т|доступн|баланс|всего|итого|период|владелец|операци|статус|реквизит|валюта|назначение|остаток|номер сч|дата откр|дата закрыт|действителен|расшифровк/i;
const PDF_DATE_RE = /\b(\d{2}[./]\d{2}[./]\d{2,4})\b/;
const PDF_TIME_ONLY_RE = /^[\d\s:.]+$/;
const PDF_TIME_IN_DESC_RE = /\b\d{1,2}:\d{2}(?::\d{2})?\b/;
const MONEY_STRICT = /(?<sign>[+−–-])\s*(?<whole>[\d\u00a0 ]+?)(?:[.,](?<frac>\d{1,2}))?\s*(?:₽|руб\.?|руб|RUB)/i;
const MONEY_LOOSE = /(?:(?<sign>[+−–-])\s*)?(?<whole>[\d\u00a0 ]{2,})(?:[.,](?<frac>\d{1,2}))?\s*(?<curr>₽|руб\.?|руб|RUB)?(?![0-9])/i;

function moneyMatches(s, strict) {
  const base = strict ? MONEY_STRICT : MONEY_LOOSE;
  const global = new RegExp(base.source, base.flags + "g");
  const out = [];
  let m;
  while ((m = global.exec(s)) !== null) {
    // эмуляция lookbehind (?<![0-9.,]): число не может начинаться после цифры/./,/
    if (m.index > 0 && /[0-9.,]/.test(s[m.index - 1])) continue;
    const sign = (m.groups.sign || "").trim();
    const curr = m.groups.curr || "";
    const wholeRaw = m.groups.whole || "";
    const whole = wholeRaw.replace(/[\s ]/g, "");
    const frac = m.groups.frac;
    const value = parseFloat(whole);
    if (Number.isNaN(value)) continue;
    // свободный режим: настоящая сумма — знак, валюта, дробь или пробел-
    // разделитель между цифрами; телефоны/даты/время отсекаются
    if (!strict && !(sign || curr || frac || /\d[  ]\d/.test(wholeRaw))) continue;
    // число, начинающее дату (26.06.2026), суммой не является
    if (!strict && /^\d{1,2}[./]\d{1,2}[./]\d{2,4}/.test(s.slice(m.index).replace(/^\s+/, ""))) continue;
    let amount = value;
    if (frac) amount += parseInt(frac, 10) / 10 ** frac.length;
    out.push({ sign, amount: Math.round(amount * 100) / 100, start: m.index });
  }
  return out;
}

function parseMoney(s, strict) {
  const matches = moneyMatches(s, strict);
  if (!matches.length) return { sign: "", amount: null };
  return { sign: matches[0].sign, amount: matches[0].amount };
}

const AUTH_CODE_RE = /^\d{4,8}\b\s*/;
const OP_BY_CARD_RE = /\s*Операция по карте(?:\s*\*{2,}[\dx]+)?\s*$/i;

// Движение денег между своими счетами и наличные — не подписки
const INTERNAL_RE = /перевод|банкомат|вклад|наличн|пополнен|списание|сбербанк|стипендия|kartavklad|vklad|sberbank onl|qr[- ]?код/i;

function cleanDesc(desc) {
  desc = desc.replace(OP_BY_CARD_RE, "");
  return desc.replace(/\s+/g, " ").replace(/^[  −.–-]+|[  −.–-]+$/g, "").trim();
}

function parsePdfDateStr(s) {
  const m = s.match(/^(\d{2})[./](\d{2})[./](\d{2,4})$/);
  if (!m) return null;
  const y = m[3].length === 2 ? 2000 + +m[3] : +m[3];
  return new Date(y, +m[2] - 1, +m[1]);
}

/** Строки PDF-выписки -> [{date, amount, description}] (порт Python-версии). */
export function transactionsFromLines(lines) {
  const hasCurrency = lines.some((l) => /₽|руб|RUB/i.test(l));
  const allSigns = lines.map((l) => moneyMatches(l, false).map((m) => m.sign));
  const strict = hasCurrency && allSigns.some((ss) => ss.some((s) => s && "−–-".includes(s)));
  const sawMinus = strict && allSigns.some((ss) => ss.some((s) => s && "−–-".includes(s)));
  const hasPlus = allSigns.some((ss) => ss.includes("+"));

  const txs = [];
  let pending = null;

  const flush = () => {
    if (pending && pending.amount !== null) {
      let desc = pending.desc.join(" ").replace(/\s+/g, " ").trim();
      desc = desc.replace(/^[ –−.-]+|[ –−.-]+$/g, "");
      desc = desc.replace(PDF_DATE_RE, " ").replace(PDF_TIME_IN_DESC_RE, " ");
      desc = cleanDesc(desc);
      if (desc) txs.push({ date: pending.date, amount: pending.amount, description: desc.slice(0, 120) });
    }
    pending = null;
  };

  let lastWasSimple = false; // предыдущая строка сама добавила транзакцию

  for (const line of lines) {
    const mDate = PDF_DATE_RE.exec(line);
    const matches = moneyMatches(line, strict);
    const sign = matches[0]?.sign ?? "";
    const amount = matches[0]?.amount ?? null;
    const isSkip = PDF_SKIP_RE.test(line);
    const hasMoney = matches.length > 0;

    if (mDate && hasMoney) {
      // однострочный формат: дата + (описание) + [сумма + остаток]
      flush();
      const d = parsePdfDateStr(mDate[1]);
      if (!d) continue;
      // в конце строки два числа: предпоследнее — сумма, последнее — остаток
      const chosen = matches.length >= 2 ? matches[matches.length - 2] : matches[0];
      let desc = line.slice(0, mDate.index) + " " + line.slice(mDate.index + mDate[0].length, chosen.start);
      desc = desc.replace(PDF_TIME_IN_DESC_RE, " ");
      desc = cleanDesc(desc);
      const debit = "−–-".includes(chosen.sign);
      const keep = sawMinus ? debit : hasPlus ? chosen.sign !== "+" : true;
      if (desc && !PDF_TIME_ONLY_RE.test(desc)) {
        if (chosen.amount !== null && keep) {
          txs.push({ date: d, amount: chosen.amount, description: desc.slice(0, 120) });
          lastWasSimple = true;
        } else {
          lastWasSimple = false; // кредитная строка — не приклеивать описание
        }
      } else {
        pending = { date: d, amount: chosen.amount !== null && keep ? chosen.amount : null, desc: [] };
        lastWasSimple = false;
      }
      continue;
    }

    if (mDate) {
      // строка с датой без суммы: два сценария склейки (описание предыдущей
      // однострочной операции либо продолжение pending с известной суммой)
      const rest = line.slice(mDate.index + mDate[0].length).trim();
      const restClean = cleanDesc(rest.replace(AUTH_CODE_RE, ""));
      if (txs && lastWasSimple && pending === null && restClean) {
        txs[txs.length - 1].description = restClean.slice(0, 120);
        lastWasSimple = false;
        continue;
      }
      if (pending !== null && pending.amount !== null && !pending.desc.length) {
        if (restClean) pending.desc.push(restClean);
        lastWasSimple = false;
        continue;
      }
      flush();
      lastWasSimple = false;
      const d = parsePdfDateStr(mDate[1]);
      if (d && !isSkip) {
        const rest2 = line.slice(mDate.index + mDate[0].length).trim();
        pending = { date: d, amount: null, desc: [] };
        if (rest2 && !PDF_SKIP_RE.test(rest2) && !PDF_TIME_ONLY_RE.test(rest2)) pending.desc.push(rest2);
      }
      continue;
    }

    if (hasMoney) {
      if (pending !== null && !isSkip) {
        const keep = sawMinus ? "−–-".includes(sign) : hasPlus ? sign !== "+" : true;
        pending.amount = keep && matches[0].amount !== null ? matches[0].amount : null;
      }
      lastWasSimple = false;
      continue;
    }

    if (pending !== null && !isSkip && !PDF_TIME_ONLY_RE.test(line)) {
      pending.desc.push(line);
    }
    lastWasSimple = false;
  }

  flush();
  return txs.sort((a, b) => a.date - b.date);
}

export const BRAND_RULES = [
  ["Яндекс Плюс", "Развлечения", "🟡",
    ["YNDX", "YANDEX_PLUS", "YANDEX PLUS", "ЯНДЕКС.ПЛЮС", "ЯНДЕКС ПЛЮС", "ЯНДЕКС+", "YANDEX.MUSIC", "ПЛЮС МУЗЫК", "МУЗЫКА ПЛЮС"]],
  ["Netflix", "Кино и видео", "🎬", ["NETFLIX", "NFLX"]],
  ["Иви", "Кино и видео", "🍿", ["IVI", "ИВИ"]],
  ["Кинопоиск", "Кино и видео", "🎥", ["КИНОПОИСК", "KINOPOISK", "KP*"]],
  ["Okko", "Кино и видео", "🎞️", ["OKKO", "ОККО"]],
  ["KION", "Кино и видео", "🎬", ["KION", "КИОН"]],
  ["Premier", "Кино и видео", "📺", ["PREMIER", "ПРЕМЬЕР"]],
  ["Амедиатека", "Кино и видео", "🍿", ["AMEDIATEKA", "АМЕДИАТЕКА"]],
  ["More.tv", "Кино и видео", "📺", ["MORE.TV", "MORETV", "МОР ТВ"]],
  ["Start", "Кино и видео", "▶️", ["START.RU", "START TV"]],
  ["Wink", "Кино и видео", "📺", ["WINK", "ВИНК"]],
  ["Megogo", "Кино и видео", "🎬", ["MEGOGO", "МЕГОГО"]],
  ["Spotify", "Музыка", "🎧", ["SPOTIFY", "SPOT*"]],
  ["Звук", "Музыка", "🎵", ["ЗВУК", "ZVUK"]],
  ["Apple Music", "Музыка", "🍎", ["APPLE MUSIC", "APPLE.COM/BILLAPPLEMUSIC"]],
  ["VK Музыка", "Музыка", "🎵", ["VK MUZ", "VK MUSIC", "МУЗЫКА VK", "VK.COM/MUSIC", "VK.COM", "SUBSCRIPTION VK"]],
  ["YouTube Premium", "Развлечения", "▶️", ["YOUTUBE", "GOOGLE*YOUTUBE"]],
  ["Telegram Premium", "Мессенджеры", "✈️", ["TG_PREMIUM", "TELEGRAM PREMIUM", "PREMIUMBOT", "T.G PREMIUM", "TEL.EGRAM"]],
  ["WORLD CLASS", "Фитнес", "🏋️", ["WORLD CLASS", "WORLDCLASS", "ФИТНЕС", "WORLD CLUB"]],
  ["СберПрайм", "Экосистема", "🟢", ["СБЕРПРАЙМ", "SBERPRIME", "ПРАЙМ"]],
  ["Яндекс Go", "Транспорт", "🚕", ["YANDEX GO", "ЯНДЕКС ТАКСИ", "ЯНДЕКС ГО", "TAXI"]],
  ["iCloud+", "Облако", "☁️", ["ICLOUD", "APPLE.COM/BILL"]],
  ["Google One", "Облако", "🌐", ["GOOGLE ONE", "GOOGLE ONEAI"]],
  ["Microsoft 365", "ПО", "💻", ["MICROSOFT 365", "MICROSOFT OFFICE", "OFFICE 365"]],
  ["Adobe", "ПО", "🎨", ["ADOBE", "CREATIVE CLOUD"]],
  ["Canva Pro", "Дизайн", "🎨", ["CANVA"]],
  ["Figma", "Дизайн", "🎨", ["FIGMA"]],
  ["Notion", "ПО", "🗂️", ["NOTION"]],
];

const ABBREV_MAP = { NFLX: "NETFLIX", SPOT: "SPOTIFY", YNDX: "YANDEX" };
const STOP_WORDS = new Set(["RU", "US", "COM", "ORG", "NET", "HTTP", "HTTPS", "WWW", "THE", "AND", "FOR", "LLC", "INC", "LTD", "GMBH"]);

const CANCEL_LINKS = {
  "Яндекс Плюс": "https://plus.yandex.ru",
  Netflix: "https://www.netflix.com/CancelPlan",
  Иви: "https://www.ivi.ru",
  "Telegram Premium": "https://telegram.org",
  Okko: "https://okko.tv",
  "VK Музыка": "https://vk.com",
  "VK Combo": "https://vk.com",
  KION: "https://kion.ru",
  Кинопоиск: "https://kinopoisk.ru",
  Spotify: "https://www.spotify.com",
  "iCloud+": "https://icloud.com",
  "YouTube Premium": "https://www.youtube.com",
  СберПрайм: "https://www.sber.ru",
  "WORLD CLASS": "https://www.worldclass.ru",
  Premier: "https://premier.one",
  Амедиатека: "https://amediateka.ru",
  "More.tv": "https://more.tv",
  Start: "https://start.ru",
  Wink: "https://wink.ru",
  Megogo: "https://megogo.ru",
  "Apple Music": "https://music.apple.com",
  "Apple TV+": "https://tv.apple.com",
  "Google One": "https://one.google.com",
  "Microsoft 365": "https://microsoft.com",
  Adobe: "https://adobe.com",
  Canva: "https://www.canva.com",
  Figma: "https://www.figma.com",
  Notion: "https://www.notion.so",
  Звук: "https://zvuk.com",
};

// Подписки, уже оплаченные в составе других (экосистемных) подписок.
const INCLUDED_IN = {
  Кинопоиск: "Яндекс Плюс",
  Звук: "СберПрайм",
  Okko: "СберПрайм",
  "VK Музыка": "VK Combo",
  "Apple Music": "Apple One",
  "Apple TV+": "Apple One",
};

export function cancelUrl(name) {
  if (CANCEL_LINKS[name]) return CANCEL_LINKS[name];
  return "https://yandex.ru/search/?text=" + encodeURIComponent("как отменить подписку " + name);
}

export function normalizeDescription(desc) {
  let s = String(desc).toUpperCase();
  s = s.replace(/HTTPS?:\/\/\S+|WWW\.\S+/g, " ");
  s = s.replace(/\S*\d\S*/g, " ");
  s = s.replace(/\.[А-ЯЁ]{2,3}\b/g, " ");
  s = s.replace(/[^A-ZА-ЯЁ ]+/g, " ");
  return s
    .split(/\s+/)
    .filter((t) => t && !STOP_WORDS.has(t) && t.length > 1)
    .map((t) => ABBREV_MAP[t] ?? t)
    .join(" ");
}

export function canonicalName(description) {
  const s = String(description).toUpperCase();
  for (const [name, cat, icon, keys] of BRAND_RULES) {
    if (keys.some((k) => s.includes(k))) return [name, cat, icon];
  }
  return null;
}

// Dice по символьным множествам слов — как финальный _dice в analyzer.py.
function dice(a, b) {
  const wa = a.toLowerCase().replace(/[_.*]/g, " ").split(/\s+/).filter(Boolean);
  const wb = b.toLowerCase().replace(/[_.*]/g, " ").split(/\s+/).filter(Boolean);
  const sa = new Set(wa.join(""));
  const sb = new Set(wb.join(""));
  if (!sa.size || !sb.size) return 0;
  let inter = 0;
  for (const c of sa) if (sb.has(c)) inter++;
  return (2 * inter) / (sa.size + sb.size);
}

function groupKey(description) {
  const canon = canonicalName(description);
  if (canon) return { kind: "brand", value: canon[0] };
  return { kind: "norm", value: normalizeDescription(description) };
}

const dateKey = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

function addMonths(d, months) {
  const m = d.getMonth() + months; // 0-based, как getMonth()
  const year = d.getFullYear() + Math.floor(m / 12);
  const month = ((m % 12) + 12) % 12;
  const day = Math.min(d.getDate(), [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]);
  return new Date(year, month, day);
}

// Кластеризация сумм (±15%) — переживает смену цены (промо → полная).
function stableCharges(items) {
  const byAmount = [...items].sort((a, b) => a.amount - b.amount);
  const clusters = [[byAmount[0]]];
  for (const t of byAmount.slice(1)) {
    const base = clusters[clusters.length - 1][Math.floor(clusters[clusters.length - 1].length / 2)].amount;
    if (Math.abs(t.amount - base) <= Math.abs(base) * 0.15) clusters[clusters.length - 1].push(t);
    else clusters.push([t]);
  }
  const newest = items.reduce((a, b) => (a.date > b.date ? a : b));
  const recurring = clusters.filter((c) => c.length >= 2 || c.includes(newest));
  const stable = recurring.flat().sort((a, b) => a.date - b.date);
  if (!stable.length) return { stable: [], current: 0 };
  const currentCluster = recurring.find((c) => c.includes(stable[stable.length - 1]));
  const amounts = currentCluster.map((t) => Math.abs(t.amount)).sort((a, b) => a - b);
  return { stable, current: amounts[Math.floor(amounts.length / 2)] };
}

export function detectSubscriptions(txs) {
  const groups = new Map();
  const normKeys = [];
  for (const t of txs) {
    let key = groupKey(t.description);
    if (key.kind === "norm") {
      const merged = normKeys.find((other) => dice(other.value, key.value) >= 0.8);
      if (merged) key = merged;
      else normKeys.push(key);
    }
    const k = key.kind + "|" + key.value;
    if (!groups.has(k)) groups.set(k, { key, items: [] });
    groups.get(k).items.push(t);
  }

  // Слепляем близкие норм-имена к известным брендам.
  for (const nk of normKeys) {
    for (const [name] of BRAND_RULES) {
      if (dice(nk.value, name) >= 0.75) {
        const src = groups.get("norm|" + nk.value);
        const dst = groups.get("brand|" + name);
        if (src && dst) dst.items.push(...src.items);
        groups.delete("norm|" + nk.value);
        break;
      }
    }
  }

  const subs = [];
  for (const { key, items } of groups.values()) {
    // внутренние переводы и вклады — не подписки, даже при регулярности
    if (INTERNAL_RE.test(key.value)) continue;
    const minEvents = key.kind === "brand" ? 2 : 3;
    if (items.length < minEvents) continue;
    const { stable, current } = stableCharges(items);
    if (stable.length < minEvents) continue;
    const gaps = stable
      .slice(1)
      .map((t, i) => Math.round((t.date - stable[i].date) / 86400000))
      .filter((g) => g >= 10)
      .sort((a, b) => a - b);
    if (!gaps.length) continue;
    const medGap = gaps[Math.floor(gaps.length / 2)];
    let period;
    if (medGap >= 20 && medGap <= 40) period = "monthly";
    else if (medGap >= 340 && medGap <= 390) period = "annual";
    else continue;

    const price = Math.abs(current);
    const monthly = period === "monthly" ? price : price / 12;
    const title = key.kind === "brand" ? key.value : key.value.replace(/\w\S*/g, (w) => w[0] + w.slice(1).toLowerCase()) || "Подписка";
    const canon = canonicalName(stable[stable.length - 1].description) || [title, "Прочее", "💳"];
    const name = key.kind === "brand" ? canon[0] : title;
    const last = stable[stable.length - 1].date;
    subs.push({
      id: (title.toLowerCase().replace(/\W+/g, "_").slice(0, 40)) || "sub",
      name,
      category: canon[1],
      icon: canon[2],
      amount: +price.toFixed(2),
      period: period === "monthly" ? "ежемесячно" : "ежегодно",
      monthly_cost: +monthly.toFixed(2),
      yearly_cost: +(monthly * 12).toFixed(2),
      charges: stable.length,
      first_charge: dateKey(stable[0].date),
      last_charge: dateKey(last),
      next_charge: dateKey(addMonths(last, period === "monthly" ? 1 : 12)),
      merchants: [...new Set(stable.map((t) => t.description))].sort(),
      price_change: detectSubscriptionPriceChange(items),
    });
  }
  subs.sort((a, b) => Math.abs(b.monthly_cost) - Math.abs(a.monthly_cost));
  return subs.map((s) => ({
    ...s,
    cancel_url: cancelUrl(s.name),
    included_in: INCLUDED_IN[s.name] ?? null,
  }));
}

const COLUMN_ALIASES = {
  date: ["date", "дата", "дата операции", "дата платежа", "operation date", "transaction date"],
  amount: ["amount", "сумма", "сумма платежа", "сумма операции", "списание", "value"],
  description: ["description", "описание", "наименование", "получатель", "merchant", "назначение", "details", "memo"],
};

function normalizeHeader(h) {
  return String(h)
    .toLowerCase()
    .replace(/ё/g, "е")
    .replace(/\(.*?\)/g, " ")
    .replace(/\s+/g, " ")
    .replace(/[^\wа-я ]/gi, " ")
    .trim();
}

function pickColumns(headers) {
  const norm = headers.map(normalizeHeader);
  const pick = {};
  // 1) точное совпадение с алиасами
  for (const [kind, aliases] of Object.entries(COLUMN_ALIASES)) {
    const i = norm.findIndex((h) => aliases.includes(h));
    if (i >= 0) pick[kind] = i;
  }
  // 2) вхождение: «сумма» ⊂ «сумма операции», «date» ⊂ «transaction date»
  for (const [kind, aliases] of Object.entries(COLUMN_ALIASES)) {
    if (pick[kind] !== undefined) continue;
    const i = norm.findIndex(
      (h) => h.length >= 3 && aliases.some((a) => h.includes(a) || a.includes(h))
    );
    if (i >= 0) pick[kind] = i;
  }
  return { pick, norm };
}

// Эвристика по содержимому: даты/числа/текст (для нестандартных заголовков).
function guessMissingColumns(rows, headers, pick) {
  const DATE_RE = /\d{1,4}[./-]\d{1,2}[./-]\d{2,4}/;
  const sample = rows.slice(0, 50);
  const stats = [];
  for (let i = 0; i < headers.length; i++) {
    if (Object.values(pick).includes(i)) continue;
    const vals = sample.map((r) => String(r[i] ?? "")).filter((v) => v.trim());
    if (!vals.length) continue;
    const dateN = vals.filter((v) => DATE_RE.test(v)).length;
    let numN = 0;
    for (const v of vals) {
      if (Number.isFinite(parseFloat(v.replace(/[^\d.,-]/g, "").replace(",", ".")))) numN++;
    }
    const textN = vals.reduce((a, v) => a + v.length, 0) / vals.length;
    stats.push({ i, dateN, numN, textN });
  }
  if (pick.date === undefined) {
    const best = stats.filter((s) => s.dateN > 0).sort((a, b) => b.dateN - a.dateN)[0];
    if (best) { pick.date = best.i; }
  }
  if (pick.amount === undefined) {
    const best = stats.filter((s) => s.i !== pick.date && s.numN > 0).sort((a, b) => b.numN - a.numN)[0];
    if (best) { pick.amount = best.i; }
  }
  if (pick.description === undefined) {
    const best = stats.filter((s) => s.i !== pick.date && s.i !== pick.amount)
      .sort((a, b) => b.textN - a.textN)[0];
    if (best) { pick.description = best.i; }
  }
}

function parseDateStr(s) {
  for (const [fmt, re] of [
    ["Y-M-D", /^(\d{4})-(\d{2})-(\d{2})$/],
    ["D.M.Y", /^(\d{2})\.(\d{2})\.(\d{4})$/],
    ["D/M/Y", /^(\d{2})\/(\d{2})\/(\d{4})$/],
    ["D.M.Yy", /^(\d{2})\.(\d{2})\.(\d{2})$/],
  ]) {
    const m = s.trim().match(re);
    if (m) {
      if (fmt === "Y-M-D") return new Date(+m[1], +m[2] - 1, +m[3]);
      const y = fmt === "D.M.Yy" ? 2000 + +m[3] : +m[3];
      return new Date(y, +m[2] - 1, +m[1]);
    }
  }
  return null;
}

function csvSplit(line, delim) {
  const out = [];
  let cur = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (c === '"') inQuotes = !inQuotes;
    else if (c === delim && !inQuotes) { out.push(cur); cur = ""; }
    else cur += c;
  }
  out.push(cur);
  return out;
}

// Ищем строку заголовков: выписки Сбера начинаются со служебных строк
// («900 www.sberbank.ru Заказано...», «Выписка по счёту...»), а не с колонок.
function findHeaderRow(lines) {
  let best = { idx: 0, delim: ",", kinds: 0 };
  const limit = Math.min(lines.length, 15);
  for (let i = 0; i < limit; i++) {
    for (const delim of [";", "\t", ","]) {
      const cells = csvSplit(lines[i], delim);
      if (cells.length < 2) continue;
      const norm = cells.map(normalizeHeader);
      let kinds = 0;
      for (const aliases of Object.values(COLUMN_ALIASES)) {
        if (aliases.some((a) => norm.some((n) => n && n.length >= 3 && (a === n || a.includes(n) || n.includes(a))))) kinds++;
      }
      if (kinds > best.kinds) best = { idx: i, delim, kinds };
    }
    if (best.kinds >= 2 && best.idx === i) break; // первая строка, похожая на заголовок
  }
  return best;
}

// CSV: строки -> [{date, amount, description}]
export function parseCsvText(text) {
  const lines = text.split(/\r?\n/).filter((l) => l.trim());
  if (!lines.length) return [];
  const headerRow = findHeaderRow(lines);
  const headers = csvSplit(lines[headerRow.idx], headerRow.delim);

  // одноколоночный CSV — текстовый дамп выписки (экспорт «как есть»):
  // отдаём все строки построчному PDF-парсеру
  if (headers.length < 2) {
    return transactionsFromLines(
      lines.map((l) => l.replace(/^"|"$/g, "").trim()).filter(Boolean)
    );
  }
  const delim = headerRow.delim;
  const { pick } = pickColumns(headers);
  const rows = lines.slice(headerRow.idx + 1).map((l) => csvSplit(l, delim));
  if (Object.values(pick).some((i) => i === undefined) || Object.keys(pick).length < 3) {
    guessMissingColumns(rows, headers, pick);
  }
  if ([pick.date, pick.amount, pick.description].some((i) => i === undefined)) {
    throw new Error(
      "Не удалось определить в CSV колонки «Дата / Сумма / Описание». Заголовки: " +
      headers.join(", ")
    );
  }
  const txs = [];
  for (const cells of rows) {
    const d = parseDateStr(cells[pick.date] || "");
    const amount = parseFloat(String(cells[pick.amount] ?? "").replace(/[^\d.,-]/g, "").replace(",", "."));
    const desc = String(cells[pick.description] ?? "").trim();
    if (d && !Number.isNaN(amount) && amount !== 0 && desc) {
      txs.push({ date: d, amount, description: desc });
    }
  }
  txs.sort((a, b) => a.date - b.date);
  return txs;
}

export function monthlyExpenseSeries(subs, months = 6) {
  const today = new Date();
  const series = [];
  for (let i = months - 1; i >= 0; i--) {
    const d = addMonths(new Date(today.getFullYear(), today.getMonth(), 1), -i);
    let total = 0;
    for (const s of subs) {
      let cur = new Date(s.first_charge + "T00:00:00");
      for (let guard = 0; guard < 240; guard++) {
        if (cur.getFullYear() > d.getFullYear() ||
            (cur.getFullYear() === d.getFullYear() && cur.getMonth() > d.getMonth())) break;
        if (cur.getMonth() === d.getMonth() && cur.getFullYear() === d.getFullYear()) total += Math.abs(s.monthly_cost);
        cur = addMonths(cur, 1);
      }
    }
    series.push({ month: `${String(d.getMonth() + 1).padStart(2, "0")}.${d.getFullYear()}`, spent: +total.toFixed(2) });
  }
  return series;
}

/** Расходы на подписки по месяцам из фактических списаний (живой график). */
export function monthlyExpenseSeriesFromTxs(txs, subs, months = 6) {
  const today = new Date();
  const merchants = new Map();
  for (const s of subs) for (const m of s.merchants) merchants.set(m, s);
  const series = [];
  for (let i = months - 1; i >= 0; i--) {
    const d = addMonths(new Date(today.getFullYear(), today.getMonth(), 1), -i);
    let total = 0;
    for (const t of txs) {
      const sub = merchants.get(t.description);
      if (!sub) continue;
      if (t.date.getFullYear() === d.getFullYear() && t.date.getMonth() === d.getMonth()) {
        total += Math.abs(t.amount);
      }
    }
    series.push({ month: `${String(d.getMonth() + 1).padStart(2, "0")}.${d.getFullYear()}`, spent: +total.toFixed(2) });
  }
  return series;
}

export function monthlyExpenseSeriesAll(txs, months = 6) {
  const today = new Date();
  const series = [];
  for (let i = months - 1; i >= 0; i--) {
    const d = addMonths(new Date(today.getFullYear(), today.getMonth(), 1), -i);
    let total = 0;
    for (const t of txs) {
      if (t.date.getFullYear() === d.getFullYear() && t.date.getMonth() === d.getMonth()) total += Math.abs(t.amount);
    }
    series.push({ month: `${String(d.getMonth() + 1).padStart(2, "0")}.${d.getFullYear()}`, spent: +total.toFixed(2) });
  }
  return series;
}

const RU_SERVICES = new Set([
  "яндекс плюс", "иви", "okko", "кион", "kion", "кинопоиск", "premier",
  "амедиатека", "more.tv", "start", "wink", "мегого", "megogo",
  "сберпрайм", "world class", "звук", "vk музыка", "яндекс go",
]);

function isRuService(name) {
  const low = String(name).trim().toLowerCase();
  if (RU_SERVICES.has(low)) return true;
  // неизвестное имя: кириллица — скорее всего российский сервис
  return !/[A-Za-z]/.test(low) && /[а-яё]/.test(low);
}

export function buildLetter({ name, amount }) {
  const today = new Date();
  const dd = String(today.getDate()).padStart(2, "0");
  const mm = String(today.getMonth() + 1).padStart(2, "0");
  const dateRu = `${dd}.${mm}.${today.getFullYear()}`;
  if (isRuService(name)) {
    const amountLine = amount
      ? ` в размере ${amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, " ")} руб./мес`
      : "";
    return `Кому: Служба поддержки «${name}»
Тема: Отказ от автопродления подписки и прекращение списаний

Здравствуйте!

Я, пользователь сервиса «${name}», настоящим уведомляю об отказе от продления
подписки (услуги) с автопродлением${amountLine} и требую прекратить списание
денежных средств с моего банковского счёта.

В соответствии со ст. 32 Закона РФ «О защите прав потребителей» потребитель
вправе отказаться от исполнения договора об оказании услуг в любое время при
оплате фактически понесённых расходов исполнителя. В соответствии со ст. 782
ГК РФ заказчик вправе отказаться от исполнения договора возмездного оказания
услуг при условии оплаты исполнителю фактически понесённых им расходов.

Прошу:
1. Отключить автоматическое продление подписки «${name}».
2. Прекратить дальнейшие списания с моего счёта.
3. Вернуть оплату за неиспользованный период, если списание уже произведено.
4. Подтвердить отключение подписки ответным письмом в течение 10 дней
   (ст. 31 Закона РФ «О защите прав потребителей»).

Дата последнего списания: ${today.toISOString().slice(0, 10)}
Дата обращения: ${dateRu}

С уважением,
Клиент сервиса «${name}»`;
  }
  // Зарубежный сервис: англоязычное письмо без ссылок на законы РФ
  const amountLine = amount
    ? ` (currently ${amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, " ")} RUB per month)`
    : "";
  return `To: ${name} Support Team
Subject: Request to cancel subscription and stop recurring charges

Hello,

I am a customer of ${name}. I kindly ask you to cancel my subscription and
disable auto-renewal${amountLine}, so that no further charges are made to
my card.

Please:
1. Cancel the subscription and auto-renewal for my account.
2. Stop all further recurring charges.
3. Refund the payment for the unused period, if one has already been charged,
   in accordance with the terms of service.
4. Confirm the cancellation by email.

Date: ${dateRu}

Best regards,
A customer of ${name}`;
}

// Детерминированная тестовая выписка для браузерного режима (без backend).
// ---------------------------------------------------------------------------
// Генератор демо-PDF в браузере: минимальный валидный PDF с текстовыми
// страницами (без зависимостей). Кириллицы нет — демо-описания латиницей.
// ---------------------------------------------------------------------------

const CYR_TO_LAT = {
  А: "A", Б: "B", В: "V", Г: "G", Д: "D", Е: "E", Ё: "E", Ж: "Zh", З: "Z",
  И: "I", Й: "Y", К: "K", Л: "L", М: "M", Н: "N", О: "O", П: "P", Р: "R",
  С: "S", Т: "T", У: "U", Ф: "F", Х: "Kh", Ц: "Ts", Ч: "Ch", Ш: "Sh",
  Щ: "Shch", Ъ: "", Ы: "Y", Ь: "", Э: "E", Ю: "Yu", Я: "Ya",
};

function toAscii(s) {
  return String(s)
    .split("")
    .map((ch) => CYR_TO_LAT[ch.toUpperCase()] ?? ch)
    .join("")
    .replace(/[^\x20-\x7E]/g, "?");
}

function pdfEscape(s) {
  return toAscii(s).split("\\").join("\\\\").split("(").join("\\(").split(")").join("\\)");
}

// Собирает PDF-байты из готовых страниц (массивы строк {text, bold, size}).
function buildPdf(pages) {
  const objs = []; // строки-объекты, индекс = номер объекта - 1
  const pageObjNums = [];
  const firstPageObj = 5;
  pages.forEach((_, i) => pageObjNums.push(firstPageObj + i * 2));

  objs[0] = "<< /Type /Catalog /Pages 2 0 R >>";
  objs[1] = "<< /Type /Pages /Kids [" + pageObjNums.map((n) => n + " 0 R").join(" ") + "] /Count " + pages.length + " >>";
  objs[2] = "<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>";
  objs[3] = "<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold >>";
  pages.forEach((pageLines, i) => {
    const pageNum = firstPageObj + i * 2;
    const contentNum = pageNum + 1;
    let stream = "";
    let y = 800;
    for (const line of pageLines) {
      if (line.text !== undefined) {
        const font = line.bold ? "/F2" : "/F1";
        stream += "BT " + font + " " + (line.size || 10) + " Tf 40 " + y + " Td (" + pdfEscape(line.text) + ") Tj ET\n";
      }
      y -= line.size ? Math.max(line.size + 6, 14) : 15;
    }
    objs[pageNum - 1] = "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
      + "/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents " + contentNum + " 0 R >>";
    objs[contentNum - 1] = "<< /Length " + stream.length + " >>\nstream\n" + stream + "endstream";
  });

  let out = "%PDF-1.4\n";
  const offsets = [];
  objs.forEach((body, i) => {
    offsets.push(out.length);
    out += (i + 1) + " 0 obj\n" + body + "\nendobj\n";
  });
  const xrefStart = out.length;
  out += "xref\n0 " + (objs.length + 1) + "\n0000000000 65535 f \n";
  for (const off of offsets) out += String(off).padStart(10, "0") + " 00000 n \n";
  out += "trailer\n<< /Size " + (objs.length + 1) + " /Root 1 0 R >>\nstartxref\n" + xrefStart + "\n%%EOF";
  const bytes = new Uint8Array(out.length);
  for (let i = 0; i < out.length; i++) bytes[i] = out.charCodeAt(i) & 0xff;
  return bytes;
}

/** Демо-PDF из текста выписки (CSV): шапка + таблица операций. */
export function makeDemoPdf(csvText) {
  const rows = csvText.split(/\r?\n/).filter((l) => l.trim()).slice(1);
  const pageLines = [];
  const today = new Date();
  pageLines.push({ text: "TEST BANK STATEMENT", bold: true, size: 14 });
  pageLines.push({ text: "Demo document for Subscription Scanner", size: 9 });
  pageLines.push({ text: "Period: " + dateKey(addMonths(today, -6)) + " - " + dateKey(today), size: 9 });
  pageLines.push({ text: "" });
  pageLines.push({ text: "Date          Description                          Amount, RUB", bold: true, size: 10 });
  pageLines.push({ text: "" });
  for (const row of rows) {
    const [d, desc, amt] = row.split(",");
    if (!d || !desc || !amt) continue;
    const dd = d.split("-").reverse().join(".");
    pageLines.push({ text: (dd + "        " + desc.slice(0, 34)).padEnd(44, " ") + " " + amt, size: 9 });
  }
  pageLines.push({ text: "" });
  pageLines.push({ text: "Generated by Subscription Scanner (demo)", size: 8 });
  // разбивка на страницы по ~48 строк
  const pages = [];
  for (let i = 0; i < pageLines.length; i += 48) pages.push(pageLines.slice(i, i + 48));
  return buildPdf(pages);
}

export function testStatementCsv() {
  const today = new Date();
  const base = new Date(today.getFullYear(), today.getMonth() - 6, 5);
  const rows = [["Date", "Description", "Amount"].join(",")];
  // джиттер ±2% — не ломает детекцию (порог цены 5%), но демо всегда новое
  const jitter = (v) => Math.round(v * (1 + (Math.random() * 0.04 - 0.02)) * 100) / 100;

  const pushMonthly = (name, amounts, startOffset = 0) => {
    amounts.forEach((amt, i) => {
      // редкий пропуск месяца, но не больше одного и не для промо/смены цены
      if (amounts.length >= 4 && Math.random() < 0.1 && i > 0 && i < amounts.length - 1) return;
      const d = addMonths(base, i + startOffset);
      const shifted = new Date(d.getFullYear(), d.getMonth(), Math.max(1, Math.min(28, d.getDate() + Math.round(Math.random() * 4 - 2))));
      rows.push(`${dateKey(shifted)},${name},-${jitter(amt).toFixed(2)}`);
    });
  };

  pushMonthly("NETFLIX.COM", [599, 599, 599, 599, 599], 1);    // подключился на 2-м месяце
  pushMonthly("KINOPOISK HD", [399, 399, 399, 399], 2);        // входит в Яндекс Плюс
  pushMonthly("START.RU", [299, 299, 299, 299, 299], 0);       // дубль категории «Кино и видео»
  pushMonthly("YANDEX_PLUS", [399, 399, 399, 399, 399, 399]);
  pushMonthly("ZVUK SUBSCRIPTION", [99, 99, 299, 299], 3);     // промо → полная цена, свежая подписка
  pushMonthly("WORLD CLASS", [3490, 3490, 4990, 4990], 2);     // подняли тариф +43%

  // случайные дополнительные подписки — демо каждый раз разное
  const extras = [
    ["OKKO.SUBSCRIPTION", 449], ["KION.RU", 249], ["VK.COM MUSIC", 299], ["MEGOGO.RU", 199],
  ];
  const extraCount = Math.floor(Math.random() * 3); // 0..2
  const pool = [...extras];
  for (let n = 0; n < extraCount && pool.length; n++) {
    const [name, amt] = pool.splice(Math.floor(Math.random() * pool.length), 1)[0];
    const count = 4 + Math.floor(Math.random() * 2);
    pushMonthly(name, Array(count).fill(amt), Math.floor(Math.random() * 2));
  }

  // шум — случайные покупки, не похожие на бренды
  const noise = [
    ["PYATEROCHKA", 340.5], ["MAGNIT", 890], ["APTEKA", 610.3],
    ["STARBUCKS", 430.7], ["KFC", 398], ["CINEMA PARK", 720],
  ];
  const noiseCount = 3 + Math.floor(Math.random() * 3);
  for (let n = 0; n < noiseCount; n++) {
    const [name, amt] = noise[Math.floor(Math.random() * noise.length)];
    const d = addMonths(base, Math.floor(Math.random() * 5));
    rows.push(`${dateKey(d)},${name},-${jitter(amt).toFixed(2)}`);
  }
  return rows.join("\n");
}
