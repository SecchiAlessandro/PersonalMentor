// Settings tab (Section 6.5) — edit purpose & ritual goals.
// Port of Views/Settings/SettingsView.swift, trimmed for the web build.

import { useEffect, useState } from "react";
import { ENERGIES, ENERGY_TITLE, type Energy } from "../models/energy";
import { energyHex } from "../theme/theme";
import { useProfile } from "../store/useStore";
import { updateProfile } from "../store/energyStore";
import type { UserProfile } from "../store/db";

type GoalKey = "goalPhysical" | "goalEmotional" | "goalMental" | "goalSpiritual";
const GOAL_KEY: Record<Energy, GoalKey> = {
  physical: "goalPhysical",
  emotional: "goalEmotional",
  mental: "goalMental",
  spiritual: "goalSpiritual",
};

export function Settings() {
  const profile = useProfile();
  const [draft, setDraft] = useState<Partial<UserProfile>>({});

  // Seed the local draft once the profile loads.
  useEffect(() => {
    if (profile) setDraft(profile);
  }, [profile?.id]);

  function setField(key: keyof UserProfile, value: string) {
    setDraft((d) => ({ ...d, [key]: value }));
  }
  function save(key: keyof UserProfile) {
    void updateProfile({ [key]: draft[key] } as Partial<UserProfile>);
  }

  return (
    <div className="mx-auto flex max-w-[480px] flex-col gap-6 px-5 py-6">
      <h1 className="font-display text-[30px] font-bold text-primary">Settings</h1>

      <Section title="Purpose">
        <textarea
          value={draft.purpose ?? ""}
          onChange={(e) => setField("purpose", e.target.value)}
          onBlur={() => save("purpose")}
          rows={3}
          className="w-full resize-none rounded-[12px] bg-surface p-3 text-[15px] text-primary outline-none"
        />
      </Section>

      <Section title="Ritual goals">
        <div className="flex flex-col gap-3">
          {ENERGIES.map((energy) => {
            const key = GOAL_KEY[energy];
            return (
              <div key={energy} className="flex items-center gap-2">
                <span className="inline-block h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: energyHex(energy) }} />
                <input
                  type="text"
                  placeholder={`${ENERGY_TITLE[energy]} ritual`}
                  value={(draft[key] as string) ?? ""}
                  onChange={(e) => setField(key, e.target.value)}
                  onBlur={() => save(key)}
                  className="w-full rounded-[12px] bg-surface p-3 text-[15px] text-primary outline-none"
                />
              </div>
            );
          })}
        </div>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-[13px] font-bold uppercase tracking-wide text-secondary">{title}</h2>
      {children}
    </section>
  );
}
