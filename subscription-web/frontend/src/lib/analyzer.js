// Порт analyzer.py + services_db.py на JavaScript — позволяет работать
// полностью в браузере (GitHub Pages) без backend.

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
      first_charge: stable[0].date.toISOString().slice(0, 10),
      last_charge: last.toISOString().slice(0, 10),
      next_charge: addMonths(last, period === "monthly" ? 1 : 12).toISOString().slice(0, 10),
      merchants: [...new Set(stable.map((t) => t.description))].sort(),
    });
  }
  subs.sort((a, b) => Math.abs(b.monthly_cost) - Math.abs(a.monthly_cost));
  return subs.map((s) => ({ ...s, cancel_url: cancelUrl(s.name), included_in: INCLUDED_IN[s.name] ?? null }));
}

const COLUMN_ALIASES = {
  date: ["date", "дата операции", "дата", "дата платежа", "operation date"],
  amount: ["amount", "сумма", "сумма платежа", "сумма операции", "списание"],
  description: ["description", "описание", "наименование", "получатель", "merchant"],
};

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

// CSV: строки -> [{date, amount, description}]
export function parseCsvText(text) {
  const lines = text.split(/\r?\n/).filter((l) => l.trim());
  if (!lines.length) return [];
  const header = lines[0];
  const delim = [";", ",", "\t"]
    .map((d) => [d, header.split(d).length])
    .sort((a, b) => b[1] - a[1])[0][0];
  const cols = header.split(delim).map((h) => h.toLowerCase().trim());
  const pick = {};
  for (const [kind, aliases] of Object.entries(COLUMN_ALIASES)) {
    pick[kind] = cols.findIndex((c) => aliases.includes(c));
  }
  if (pick.date < 0 || pick.amount < 0 || pick.description < 0) {
    throw new Error("В CSV нет нужных колонок: Дата / Сумма / Описание. Найдены: " + cols.join(", "));
  }
  const txs = [];
  for (const line of lines.slice(1)) {
    const cells = csvSplit(line, delim);
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

export function buildLetter({ name, amount }) {
  const amountLine = amount ? ` в размере ${amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, " ")} руб./мес` : "";
  const today = new Date();
  const dd = String(today.getDate()).padStart(2, "0");
  const mm = String(today.getMonth() + 1).padStart(2, "0");
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
Дата обращения: ${dd}.${mm}.${today.getFullYear()}

С уважением,
Клиент сервиса «${name}»`;
}

// Детерминированная тестовая выписка для браузерного режима (без backend).
export function testStatementCsv() {
  const today = new Date();
  const base = new Date(today.getFullYear(), today.getMonth() - 6, 5);
  const rows = [["Date", "Description", "Amount"].join(",")];
  const pushMonthly = (name, amounts, startOffset = 0) => {
    amounts.forEach((amt, i) => {
      const d = addMonths(base, i + startOffset);
      rows.push(`${d.toISOString().slice(0, 10)},${name},-${amt.toFixed(2)}`);
    });
  };
  pushMonthly("NETFLIX.COM", [599, 599, 599, 599, 599]);
  pushMonthly("YANDEX_PLUS", [399, 399, 399, 399, 399, 399]);
  pushMonthly("KINOPOISK HD", [399, 399, 399, 399]);           // входит в Яндекс Плюс
  pushMonthly("ZVUK SUBSCRIPTION", [99, 99, 299, 299], 3);     // промо → полная цена, свежая подписка
  pushMonthly("WORLD CLASS", [3490, 3490, 3490, 3490]);
  // шум — только в первых месяцах и без похожих на бренды имён
  const noise = [
    ["PYATEROCHKA", 340.5], ["MAGNIT", 890], ["APTEKA", 610.3],
  ];
  noise.forEach(([name, amt], i) => {
    const d = addMonths(base, i);
    rows.push(`${d.toISOString().slice(0, 10)},${name},-${amt.toFixed(2)}`);
  });
  return rows.join("\n");
}
