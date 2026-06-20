// The daily check-in — 4 Yes/No checkbox questions derived from the user's
// ritual goals, then deterministic scoring → coach → upsert today's entry.
// Port of Views/CheckIn/CheckInView.swift (slider replaced with checkbox).

import { useEffect, useMemo, useState } from "react";
import {
  bottleneck,
  questionEnergy,
  type CheckInQuestion,
  type Energy,
  ENERGY_TITLE,
} from "../models/energy";
import { energyHex } from "../theme/theme";
import { coachFor } from "../coach";
import { prepareDailyQuestions } from "../coach/questions";
import { cumulativeScores } from "../models/energy";
import { currentProfile, recentEntries, upsert, previousEntry } from "../store/energyStore";
import { PrimaryButton } from "../components/ui";

export function CheckIn({ onClose }: { onClose: () => void }) {
  const [questions, setQuestions] = useState<CheckInQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, boolean>>({});
  const [note, setNote] = useState("");
  const [purpose, setPurpose] = useState("");
  const [loading, setLoading] = useState(true);
  const [scoring, setScoring] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [recent, profile] = await Promise.all([recentEntries(14), currentProfile()]);
      const qs = await prepareDailyQuestions(profile, recent);
      if (cancelled) return;
      setPurpose(profile?.purpose?.trim() ?? "");
      setQuestions(qs);
      setAnswers((prev) => {
        const next = { ...prev };
        for (const q of qs) if (next[q.id] === undefined) next[q.id] = false;
        return next;
      });
      setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function submit() {
    setScoring(true);

    // Convert boolean answers to 0–10 scale: Yes → 10, No → 0
    const rawAnswers: Record<string, number> = {};
    for (const [id, checked] of Object.entries(answers)) rawAnswers[id] = checked ? 10 : 0;

    // Identify missed goals as short energy labels (e.g. "Mental") — not the full question text
    const missedGoals = questions
      .filter((q) => !answers[q.id])
      .map((q) => {
        const energy = questionEnergy(q);
        return energy ? ENERGY_TITLE[energy as Energy] : q.energy;
      });

    // Compute cumulative ±1 scores from the previous day's baseline
    const [profile, prevEntry] = await Promise.all([currentProfile(), previousEntry()]);
    const scores = cumulativeScores(rawAnswers, prevEntry);
    const result = await coachFor(profile, scores, bottleneck(scores), missedGoals);

    await upsert({
      scores,
      coaching: result.coaching,
      ritualNudge: result.ritualNudge,
      coachSource: result.source,
      rawAnswers,
      note: note.trim() === "" ? undefined : note,
    });
    setScoring(false);
    onClose();
  }

  return (
    <div className="flex flex-col">
      <div className="flex items-center justify-between px-5 pt-5">
        <button className="text-secondary" onClick={onClose}>
          Cancel
        </button>
        <span className="text-[13px] font-semibold text-secondary">Check-in</span>
        <span className="w-12" />
      </div>

      <div className="flex flex-col gap-7 px-5 py-6">
        <div className="flex flex-col gap-1.5">
          <h1 className="font-display text-[26px] font-bold text-primary">How did you do today?</h1>
          {purpose && (
            <p className="text-[13px] italic text-secondary">With your why in mind: "{purpose}"</p>
          )}
        </div>

        {loading ? (
          <p className="py-10 text-center text-secondary">Preparing your questions…</p>
        ) : (
          <>
            {questions.map((q) => (
              <GoalCheckRow
                key={q.id}
                question={q}
                checked={answers[q.id] ?? false}
                onChange={(v) => setAnswers((a) => ({ ...a, [q.id]: v }))}
              />
            ))}

            <div className="flex flex-col gap-2">
              <label className="text-[13px] font-bold text-secondary">Note (optional)</label>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                rows={3}
                placeholder="Anything worth remembering about today…"
                className="w-full resize-none rounded-[12px] bg-surface p-3 text-[15px] text-primary outline-none"
              />
            </div>
          </>
        )}
      </div>

      <div className="sticky bottom-0 px-4 pb-5 pt-2" style={{ background: "var(--canvas)" }}>
        <PrimaryButton
          title={scoring ? "Scoring…" : "See my energy"}
          disabled={loading || scoring}
          onClick={submit}
        />
      </div>
    </div>
  );
}

function GoalCheckRow({
  question,
  checked,
  onChange,
}: {
  question: CheckInQuestion;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  const energy = questionEnergy(question);
  const tint = useMemo(() => (energy ? energyHex(energy) : "#888"), [energy]);

  return (
    <label
      className="flex cursor-pointer items-center gap-4 rounded-[18px] bg-surface p-4"
      style={{ borderLeft: `4px solid ${tint}` }}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="sr-only"
      />
      <div
        className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full border-2 transition-colors"
        style={{
          borderColor: tint,
          background: checked ? tint : "transparent",
        }}
      >
        {checked && (
          <svg viewBox="0 0 12 10" className="h-3.5 w-3.5 fill-none stroke-white stroke-2">
            <polyline points="1,5 4.5,9 11,1" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </div>
      <p className="text-[16px] font-medium text-primary">{question.text}</p>
    </label>
  );
}
