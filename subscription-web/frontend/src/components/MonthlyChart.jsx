import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip,
} from "recharts";

const fmt = (n) => `${Math.round(n).toLocaleString("ru-RU")} ₽`;

export default function MonthlyChart({ data }) {
  return (
    <section className="card p-6">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="font-bold text-white">Расходы на подписки по месяцам</h2>
          <p className="text-xs text-slate-500">Динамика за последние 6 месяцев</p>
        </div>
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="sberFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#21A038" stopOpacity={0.5} />
                <stop offset="100%" stopColor="#21A038" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
            <XAxis dataKey="month" tick={{ fill: "#64748B", fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#64748B", fontSize: 12 }} axisLine={false} tickLine={false}
                   tickFormatter={(v) => `${v / 1000}к`} />
            <Tooltip
              contentStyle={{
                background: "#0E1526", border: "1px solid #1E293B",
                borderRadius: 12, color: "#E2E8F0",
              }}
              formatter={(v) => [fmt(v), "Расходы"]}
            />
            <Area type="monotone" dataKey="spent" stroke="#21A038" strokeWidth={2.5}
                  fill="url(#sberFill)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
