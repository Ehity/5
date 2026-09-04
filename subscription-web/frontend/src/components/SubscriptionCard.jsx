import { CalendarClock, Repeat, ExternalLink, PackageCheck } from "lucide-react";

const fmt = (n) => Math.round(n).toLocaleString("ru-RU");

const MONTHS = [
  "января", "февраля", "марта", "апреля", "мая", "июня",
  "июля", "августа", "сентября", "октября", "ноября", "декабря",
];

function fmtDate(iso) {
  const d = new Date(iso);
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}

function daysLeft(iso) {
  return Math.ceil((new Date(iso) - new Date()) / 86400000);
}

export default function SubscriptionCard({ sub, onCancel }) {
  const days = daysLeft(sub.next_charge);
  return (
    <div className="card group p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-slate-600 hover:shadow-xl hover:shadow-black/40">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-800 text-2xl">
            {sub.icon}
          </div>
          <div>
            <h3 className="font-semibold text-white">{sub.name}</h3>
            <span className="text-xs text-slate-500">{sub.category}</span>
            {sub.included_in && (
              <span
                className="mt-1 flex w-fit items-center gap-1 rounded-full bg-amber-500/10 px-2 py-0.5 text-[11px] text-amber-400"
                title={`Это списание дублирует подписку «${sub.included_in}», за которую вы уже платите`}
              >
                <PackageCheck size={11} /> Входит в «{sub.included_in}»
              </span>
            )}
          </div>
        </div>
        <span className="flex items-center gap-1 rounded-full bg-slate-800 px-2.5 py-1 text-[11px] text-slate-400">
          <Repeat size={11} /> {sub.charges} списаний
        </span>
      </div>

      <div className="mt-4 flex items-baseline gap-1">
        <span className="text-3xl font-bold text-white">{fmt(sub.monthly_cost)} ₽</span>
        <span className="text-sm text-slate-500">/ мес</span>
        <span className="ml-auto text-sm text-slate-500">
          {fmt(sub.yearly_cost)} ₽/год
        </span>
      </div>

      <div className="mt-3 flex items-center justify-between rounded-xl bg-slate-800/50 px-3 py-2 text-xs">
        <span className="flex items-center gap-1.5 text-slate-400">
          <CalendarClock size={13} /> Следующее списание
        </span>
        <span className="text-slate-300">
          {fmtDate(sub.next_charge)}
          {days >= 0 && (
            <span className={days <= 3 ? "ml-2 text-amber-400" : "ml-2 text-emerald-400"}>
              ({days} дн.)
            </span>
          )}
        </span>
      </div>

      <div className="mt-4 flex items-center gap-3">
        <button
          onClick={() => onCancel(sub)}
          className="flex-1 rounded-xl bg-gradient-to-r from-rose-500 to-red-500 py-2.5 text-sm font-semibold text-white shadow-lg shadow-rose-500/20 transition hover:brightness-110 active:scale-[0.99]"
        >
          Отменить подписку
        </button>
        {sub.cancel_url && (
          <a
            href={sub.cancel_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-700 text-slate-400 transition hover:border-emerald-500 hover:text-emerald-400 hover:shadow-lg"
            title="Перейти к управлению подпиской"
          >
            <ExternalLink size={18} />
          </a>
        )}
      </div>
    </div>
  );
}
