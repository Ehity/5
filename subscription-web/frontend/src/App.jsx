import { useEffect, useState } from "react";
import { Sparkles, LayoutGrid } from "lucide-react";

import Header from "./components/Header.jsx";
import SavingsBanner from "./components/SavingsBanner.jsx";
import UploadZone from "./components/UploadZone.jsx";
import SubscriptionCard from "./components/SubscriptionCard.jsx";
import LetterModal from "./components/LetterModal.jsx";
import MonthlyChart from "./components/MonthlyChart.jsx";
import { fetchSubscriptions, uploadStatement, resetToDemo } from "./api.js";

export default function App() {
  const [data, setData] = useState(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);
  const [modalSub, setModalSub] = useState(null);
  const [cancelled, setCancelled] = useState([]);

  async function load() {
    try {
      const d = await fetchSubscriptions();
      setData(d);
      setConnected(true);
      setCancelled([]);
      setError(null);
    } catch {
      setConnected(false);
      setError("Не удалось подключиться к API. Запустите backend: uvicorn main:app --port 8000");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleUploaded(file) {
    const d = await uploadStatement(file);
    setData(d);
    setCancelled([]);
    return d;
  }

  async function handleReset() {
    await resetToDemo();
    load();
  }

  function handleCancel(sub) {
    setModalSub(sub);
    setCancelled((prev) => (prev.includes(sub.id) ? prev : [...prev, sub.id]));
  }

  if (!data) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4">
        <div className="sber-gradient h-14 w-14 animate-pulse rounded-2xl" />
        <p className="text-slate-500">{error || "Подключаемся к серверу…"}</p>
        {error && (
          <button onClick={load} className="rounded-xl bg-emerald-500/10 px-4 py-2 text-sm text-emerald-400">
            Повторить
          </button>
        )}
      </div>
    );
  }

  const active = data.subscriptions.filter((s) => !cancelled.includes(s.id));
  const savedYearly = data.subscriptions
    .filter((s) => cancelled.includes(s.id))
    .reduce((acc, s) => acc + s.yearly_cost, 0);

  return (
    <div className="min-h-screen">
      <Header connected={connected} mock={data.mock} />

      <main className="mx-auto max-w-7xl space-y-6 px-6 py-6">
        <SavingsBanner
          totalYearly={savedYearly > 0 ? savedYearly : data.total_yearly}
          totalMonthly={savedYearly > 0 ? savedYearly / 12 : data.total_monthly}
          cancelledCount={cancelled.length}
        />

        <UploadZone
          onUploaded={handleUploaded}
          onReset={handleReset}
          mock={data.mock}
          message={data.message}
        />

        <section>
          <div className="mb-4 flex items-center gap-2">
            <LayoutGrid size={18} className="text-emerald-400" />
            <h2 className="text-lg font-bold text-white">
              Найденные подписки
              <span className="ml-2 rounded-full bg-slate-800 px-2.5 py-0.5 text-sm font-semibold text-slate-400">
                {active.length}
              </span>
            </h2>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {active.map((sub) => (
              <SubscriptionCard key={sub.id} sub={sub} onCancel={handleCancel} />
            ))}
          </div>
          {active.length === 0 && (
            <div className="card flex flex-col items-center gap-2 p-10 text-center">
              <Sparkles size={28} className="text-emerald-400" />
              <p className="font-semibold text-white">Все подписки отмечены к отмене!</p>
              <p className="text-sm text-slate-500">
                Экономия {Math.round(savedYearly).toLocaleString("ru-RU")} ₽ в год — скопируйте
                заявления из писем и отправьте в поддержку.
              </p>
            </div>
          )}
        </section>

        <MonthlyChart data={data.monthly} />

        <footer className="pb-6 pt-2 text-center text-xs text-slate-600">
          Сбер.Сканер Подписок · хакатонный MVP · FastAPI + React + Tailwind CSS
        </footer>
      </main>

      {modalSub && <LetterModal sub={modalSub} onClose={() => setModalSub(null)} />}
    </div>
  );
}
