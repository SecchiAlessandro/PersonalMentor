// The Today tab (Section 6.2) — the Energy Wheel, balance hero metric, coach
// card, and the check-in CTA. Port of Views/Today/DashboardView.swift.

import { useState } from "react";
import {
  bottleneck,
  overallEnergy,
  ENERGY_BLURB,
  ENERGY_TITLE,
  type Energy,
  type EnergyScores,
} from "../models/energy";
import { energyHex } from "../theme/theme";
import { useEntriesInRange, useLatestEntry, useProfile, useTodaysEntry } from "../store/useStore";
import { EnergyWheel } from "../components/EnergyWheel";
import { Sparkline } from "../components/Sparkline";
import { Card, PillLabel, PrimaryButton } from "../components/ui";
import { Modal } from "../components/Modal";
import { CheckIn } from "./CheckIn";

const ZERO: EnergyScores = { physical: 0, emotional: 0, mental: 0, spiritual: 0, recovery: 0 };

export function Dashboard() {
  const today = useTodaysEntry();
  const latest = useLatestEntry();
  const [showCheckIn, setShowCheckIn] = useState(false);
  const [selected, setSelected] = useState<Energy | null>(null);

  // Show today's entry if available; otherwise fall back to the most recent
  // entry so the wheel reflects the last known running scores (freeze behaviour).
  const scores: EnergyScores = today ?? latest ?? ZERO;
  const overall = overallEnergy(scores);
  const floor = bottleneck(scores);

  const balanceRead = (() => {
    if (!today) return "No check-in yet today — your wheel is waiting.";
    if (overall >= 75) return "Your overall energy is high. Keep the momentum.";
    if (overall >= 50) return `Overall energy at ${overall}. ${ENERGY_TITLE[floor]} is your current floor — lift the weakest.`;
    return `Low overall energy. Restore ${ENERGY_TITLE[floor].toLowerCase()} first.`;
  })();

  const todayLabel = new Date().toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="mx-auto flex max-w-[480px] flex-col gap-6 px-5 py-6">
      <header>
        <div className="text-[14px] font-semibold text-secondary">{todayLabel}</div>
        <h1 className="font-display text-[30px] font-bold text-primary">Full Engagement</h1>
      </header>

      <EnergyWheel scores={scores} onSelect={setSelected} />

      <div className="flex flex-col items-center gap-1.5">
        <div className="font-display text-[64px] font-bold leading-none text-accent">{overall}</div>
        <p className="text-center text-[15px] text-secondary">{balanceRead}</p>
      </div>

      {today && (
        <Card>
          <div className="flex flex-col gap-3">
            <div className="flex items-center text-secondary">
              <span className="mr-1.5">✨</span>
              <span className="text-[13px] font-bold">Coach</span>
              <span className="ml-1.5 text-[11px] font-medium opacity-80">
                {today.coachSource === "ai" ? "· AI" : "· rule-based"}
              </span>
              <span className="ml-auto">
                <PillLabel text={`Floor: ${ENERGY_TITLE[today.bottleneck as Energy]}`} color={energyHex(today.bottleneck as Energy)} />
              </span>
            </div>
            <p className="text-[16px] text-primary">{today.coaching}</p>
            {today.ritualNudge && (
              <>
                <hr style={{ borderColor: "var(--hairline)" }} />
                <div className="flex items-start gap-2 text-secondary">
                  <span>☑️</span>
                  <span className="text-[14px]">{today.ritualNudge}</span>
                </div>
              </>
            )}
          </div>
        </Card>
      )}

      <PrimaryButton
        title={today ? "Update today's check-in" : "Begin daily check-in"}
        onClick={() => setShowCheckIn(true)}
      />

      <Modal open={showCheckIn} onClose={() => setShowCheckIn(false)}>
        <CheckIn onClose={() => setShowCheckIn(false)} />
      </Modal>

      <Modal open={selected !== null} onClose={() => setSelected(null)}>
        {selected && <EnergyDetailSheet energy={selected} />}
      </Modal>
    </div>
  );
}

/// Tap-to-detail sheet (Section 5): %, goal, 14-day mini-trend, framework blurb.
function EnergyDetailSheet({ energy }: { energy: Energy }) {
  const today = useTodaysEntry();
  const profile = useProfile();
  const recent = useEntriesInRange(14);

  const current = today ? today[energy] : 0;
  const goal =
    profile?.[`goal${ENERGY_TITLE[energy]}` as "goalPhysical" | "goalEmotional" | "goalMental" | "goalSpiritual"] ??
    "";
  const trend = (recent ?? []).map((e) => e[energy]);

  return (
    <div className="flex flex-col gap-5 p-6">
      <div className="flex items-center gap-2">
        <span className="inline-block h-3.5 w-3.5 rounded-full" style={{ background: energyHex(energy) }} />
        <h2 className="font-display text-[28px] font-bold text-primary">{ENERGY_TITLE[energy]}</h2>
        <span className="ml-auto font-display text-[36px] font-bold" style={{ color: energyHex(energy) }}>
          {current}
        </span>
      </div>

      <p className="text-[15px] text-secondary">{ENERGY_BLURB[energy]}</p>

      {goal && (
        <Card>
          <div className="text-[12px] font-bold text-secondary">Your ritual goal</div>
          <div className="mt-1.5 text-[16px] text-primary">{goal}</div>
        </Card>
      )}

      <div className="text-[12px] font-bold text-secondary">Last 14 days</div>
      <Sparkline values={trend} color={energyHex(energy)} />
    </div>
  );
}
