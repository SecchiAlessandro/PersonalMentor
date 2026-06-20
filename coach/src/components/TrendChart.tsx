// Multi-line trend of the four energies + a dedicated balance area chart
// (Section 6.4). Port of Views/History/TrendChart.swift, built on Recharts.

import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ENERGIES, ENERGY_TITLE, balance } from "../models/energy";
import type { EnergyEntry } from "../store/db";
import { BALANCE_ACCENT, energyHex } from "../theme/theme";

function fmtDay(day: number): string {
  return new Date(day).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function TrendChart({ entries }: { entries: EnergyEntry[] }) {
  const data = entries.map((e) => ({
    day: fmtDay(e.day),
    physical: e.physical,
    emotional: e.emotional,
    mental: e.mental,
    spiritual: e.spiritual,
  }));

  return (
    <div className="h-[240px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
          <CartesianGrid stroke="var(--hairline)" vertical={false} />
          <XAxis dataKey="day" tick={{ fontSize: 11, fill: "var(--text-secondary)" }} minTickGap={24} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "var(--text-secondary)" }} />
          <Tooltip
            contentStyle={{
              background: "var(--surface)",
              border: "1px solid var(--hairline)",
              borderRadius: 12,
              color: "var(--text-primary)",
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {ENERGIES.map((energy) => (
            <Line
              key={energy}
              type="monotone"
              dataKey={energy}
              name={ENERGY_TITLE[energy]}
              stroke={energyHex(energy)}
              strokeWidth={2.5}
              dot={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function BalanceTrendChart({ entries }: { entries: EnergyEntry[] }) {
  const data = entries.map((e) => ({ day: fmtDay(e.day), balance: balance(e) }));

  return (
    <div className="h-[160px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
          <defs>
            <linearGradient id="balanceFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={BALANCE_ACCENT} stopOpacity={0.4} />
              <stop offset="100%" stopColor={BALANCE_ACCENT} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--hairline)" vertical={false} />
          <XAxis dataKey="day" tick={{ fontSize: 11, fill: "var(--text-secondary)" }} minTickGap={24} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "var(--text-secondary)" }} />
          <Area
            type="monotone"
            dataKey="balance"
            stroke={BALANCE_ACCENT}
            strokeWidth={2.5}
            fill="url(#balanceFill)"
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
