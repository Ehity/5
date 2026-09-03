import { ShieldCheck, Wifi, WifiOff } from "lucide-react";

export default function Header({ connected, mock }) {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-800 bg-[#0B0F1A]/80 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="sber-gradient flex h-11 w-11 items-center justify-center rounded-2xl text-xl font-black text-white shadow-lg shadow-emerald-500/20">
            ₽
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white">
              Сбер<span className="text-emerald-400">.</span>Сканер Подписок
            </h1>
            <p className="text-xs text-slate-500">
              Найдём забытые подписки и вернём ваши деньги
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {mock ? (
            <span className="flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-xs font-medium text-amber-400">
              <ShieldCheck size={14} /> Демо-данные
            </span>
          ) : (
            <span className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-400">
              <ShieldCheck size={14} /> Ваша выписка
            </span>
          )}
          <span
            className={`flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium ${
              connected
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                : "border-rose-500/30 bg-rose-500/10 text-rose-400"
            }`}
          >
            {connected ? <Wifi size={14} /> : <WifiOff size={14} />}
            {connected ? "API подключён" : "API недоступен"}
          </span>
        </div>
      </div>
    </header>
  );
}
