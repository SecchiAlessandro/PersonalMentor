// Onboarding / Setup (Section 6.1) — purpose statement + one ritual goal per
// energy. Port of Views/Onboarding/SetupView.swift, trimmed for the web build
// (no AI step, no privacy step).

import { useState } from "react";
import { ENERGIES, ENERGY_BLURB, ENERGY_TITLE, type Energy } from "../models/energy";
import { energyHex } from "../theme/theme";
import { DEFAULT_PURPOSE } from "../store/db";
import { ensureProfile, updateProfile } from "../store/energyStore";
import { PrimaryButton } from "../components/ui";

const TOTAL_STEPS = 2;

const PLACEHOLDERS: Record<Energy, string> = {
  physical: "e.g. 50 push-ups, or jog 20 min",
  emotional: "e.g. call a friend, or write 3 gratitudes",
  mental: "e.g. 90-min deep work block, no phone",
  spiritual: "e.g. 5 min reflection on my purpose",
};

export function Onboarding({ onComplete }: { onComplete: () => void }) {
  const [step, setStep] = useState(0);
  const [purpose, setPurpose] = useState(DEFAULT_PURPOSE);
  const [goals, setGoals] = useState<Partial<Record<Energy, string>>>({});

  async function finish() {
    await ensureProfile();
    await updateProfile({
      purpose,
      goalPhysical: goals.physical ?? "",
      goalEmotional: goals.emotional ?? "",
      goalMental: goals.mental ?? "",
      goalSpiritual: goals.spiritual ?? "",
      coachEnabled: false,
    });
    onComplete();
  }

  return (
    <div className="flex min-h-screen flex-col bg-canvas">
      {/* Progress */}
      <div className="px-5 pt-6">
        <div className="h-1.5 w-full overflow-hidden rounded-full" style={{ background: "var(--hairline)" }}>
          <div
            className="h-full rounded-full bg-accent transition-all"
            style={{ width: `${((step + 1) / TOTAL_STEPS) * 100}%` }}
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-8">
        {step === 0 && (
          <StepScaffold
            title="Your why"
            subtitle="Spiritual energy is the apex of the pyramid — a purpose beyond self-interest. Start there."
          >
            <label className="mb-2 block text-[14px] font-bold text-secondary">What is your purpose?</label>
            <textarea
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              rows={4}
              className="w-full resize-none rounded-[14px] bg-surface p-3.5 text-[16px] text-primary outline-none"
            />
          </StepScaffold>
        )}

        {step === 1 && (
          <StepScaffold
            title="One daily habit each"
            subtitle="Each habit becomes a Yes/No check-in question every day. Be specific and actionable — e.g. '50 push-ups', 'jog 20 min', 'hike with GF'."
          >
            <div className="flex flex-col gap-3.5">
              {ENERGIES.map((energy) => (
                <div key={energy} className="flex flex-col gap-1.5">
                  <div className="flex items-center gap-2">
                    <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: energyHex(energy) }} />
                    <span className="text-[14px] font-bold text-primary">{ENERGY_TITLE[energy]}</span>
                    <span className="ml-auto text-[11px] text-secondary">{ENERGY_BLURB[energy]}</span>
                  </div>
                  <input
                    type="text"
                    value={goals[energy] ?? ""}
                    placeholder={PLACEHOLDERS[energy]}
                    onChange={(e) => setGoals((g) => ({ ...g, [energy]: e.target.value }))}
                    className="w-full rounded-[12px] bg-surface p-3 text-[15px] text-primary outline-none"
                  />
                </div>
              ))}
            </div>
          </StepScaffold>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center gap-3 px-5 pb-8 pt-2">
        {step > 0 && (
          <button className="text-secondary" onClick={() => setStep((s) => s - 1)}>
            Back
          </button>
        )}
        <div className="ml-auto w-[200px]">
          <PrimaryButton
            title={step === TOTAL_STEPS - 1 ? "Begin" : "Next"}
            onClick={() => (step < TOTAL_STEPS - 1 ? setStep((s) => s + 1) : finish())}
          />
        </div>
      </div>
    </div>
  );
}

function StepScaffold({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto flex max-w-[480px] flex-col gap-4">
      <h1 className="font-display text-[30px] font-bold text-primary">{title}</h1>
      <p className="text-[15px] text-secondary">{subtitle}</p>
      <div className="pt-2">{children}</div>
    </div>
  );
}
