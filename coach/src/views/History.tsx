// History tab (Section 6.4) — range-toggled energy trend, balance trend, and
// ritual streaks. Port of Views/History/HistoryView.swift.

import { useState } from "react";
import { ENERGY_TITLE, type Energy } from "../models/energy";
import { energyHex, BALANCE_ACCENT } from "../theme/theme";
import { useEntriesInRange, useRituals } from "../store/useStore";
import { BalanceTrendChart, TrendChart } from "../components/TrendChart";
import { Card, SectionHeader } from "../components/ui";
import type { Ritual } from "../store/db";

const RANGES = [14, 30, 90] as const;

export function History() {
  const [range, setRange] = useState<(typeof RANGES)[number]>(14);
  const entries = useEntriesInRange(range) ?? [];
  const rituals = useRituals() ?? [];

  return (
    <div className="mx-auto flex max-w-[640px] flex-col gap-6 px-5 py-6">
      <h1 className="font-display text-[30px] font-bold text-primary">History</h1>

      {/* Segmented range picker */}
      <div className="flex rounded-[12px] p-1" style={{ background: "var(--hairline)" }}>
        {RANGES.map((r) => (
          <button
            key={r}
            onClick={() => setRange(r)}
            className="flex-1 rounded-[9px] py-1.5 text-[14px] font-semibold transition-colors"
            style={
              range === r
                ? { background: "var(--surface)", color: "var(--text-primary)" }
                : { color: "var(--text-secondary)" }
            }
          >
            {r}d
          </button>
        ))}
      </div>

      {entries.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-16 text-secondary">
          <span className="text-4xl">📈</span>
          <p className="text-[15px]">No check-ins in this range yet.</p>
        </div>
      ) : (
        <>
          <SectionHeader title="Four energies" />
          <Card>
            <TrendChart entries={entries} />
          </Card>

          <SectionHeader title="Balance" />
          <Card>
            <BalanceTrendChart entries={entries} />
          </Card>
        </>
      )}

      {rituals.length > 0 && (
        <>
          <SectionHeader title="Ritual streaks" />
          {rituals.map((ritual) => (
            <RitualRow key={ritual.id} ritual={ritual} />
          ))}
        </>
      )}
    </div>
  );
}

function RitualRow({ ritual }: { ritual: Ritual }) {
  const energy = ritual.energy as Energy;
  const doneToday = ritual.lastDone ? new Date(ritual.lastDone).toDateString() === new Date().toDateString() : false;
  return (
    <Card>
      <div className="flex items-center">
        <span className="mr-3 inline-block h-3 w-3 rounded-full" style={{ background: energyHex(energy) }} />
        <div className="flex flex-col">
          <span className="text-[15px] font-medium text-primary">{ritual.text || ENERGY_TITLE[energy]}</span>
          <span className="text-[12px] text-secondary">{ENERGY_TITLE[energy]}</span>
        </div>
        <span
          className="ml-auto flex items-center gap-1 text-[15px] font-bold"
          style={{ color: doneToday ? BALANCE_ACCENT : "var(--text-secondary)" }}
        >
          🔥 {ritual.streak}
        </span>
      </div>
    </Card>
  );
}
