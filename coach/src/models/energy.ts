// Port of Models/EnergyDomain.swift — the deterministic core.
// Scoring is ALWAYS computed here, never produced by a model (Section 7).

// MARK: - Energy

/// The four energies of the Full Engagement pyramid. Order is pyramid order
/// (physical = foundation … spiritual = apex).
export const ENERGIES = ["physical", "emotional", "mental", "spiritual"] as const;
export type Energy = (typeof ENERGIES)[number];

export const ENERGY_TITLE: Record<Energy, string> = {
  physical: "Physical",
  emotional: "Emotional",
  mental: "Mental",
  spiritual: "Spiritual",
};

/// One-line framework blurb shown in the detail sheet (Section 9).
export const ENERGY_BLURB: Record<Energy, string> = {
  physical: "The fuel: capacity to expend & recover.",
  emotional: "The quality: positive vs. fear-driven.",
  mental: "The focus: concentration & realistic optimism.",
  spiritual: "The why: purpose & deeply held values.",
};

/// Pyramid level, 0 = foundation. Used by the coach's pyramid reasoning.
export const PYRAMID_LEVEL: Record<Energy, number> = {
  physical: 0,
  emotional: 1,
  mental: 2,
  spiritual: 3,
};

// MARK: - Scores

/// Deterministic scores for a single check-in (0…100 each).
export interface EnergyScores {
  physical: number;
  emotional: number;
  mental: number;
  spiritual: number;
  recovery: number;
}

export function scoreValue(scores: EnergyScores, energy: Energy): number {
  return scores[energy];
}

/// Tight spread = high balance. `max(0, 100 - (max - min))`.
export function balance(scores: EnergyScores): number {
  const values = [scores.physical, scores.emotional, scores.mental, scores.spiritual];
  const hi = Math.max(...values);
  const lo = Math.min(...values);
  return Math.max(0, 100 - (hi - lo));
}

/// Arithmetic mean of the four energies (0…100).
export function overallEnergy(scores: EnergyScores): number {
  const values = [scores.physical, scores.emotional, scores.mental, scores.spiritual];
  return Math.round(values.reduce((a, b) => a + b, 0) / values.length);
}

/// The weakest energy — the system's current floor. Ties break toward the lower
/// pyramid level (the foundation matters more).
export function bottleneck(scores: EnergyScores): Energy {
  return ENERGIES.reduce((lhs, rhs) => {
    if (scores[lhs] !== scores[rhs]) return scores[lhs] < scores[rhs] ? lhs : rhs;
    return PYRAMID_LEVEL[lhs] < PYRAMID_LEVEL[rhs] ? lhs : rhs;
  });
}

/// True when the physical floor is both weak and the bottleneck — the coach must
/// flag that it caps everything above it.
export function physicalFloorCapping(scores: EnergyScores): boolean {
  return scores.physical < 50 && bottleneck(scores) === "physical";
}

// MARK: - Scoring

/// Maps a list of slider values (0…10) to a 0…100 score.
export function scoreForAnswers(answers: number[]): number {
  if (answers.length === 0) return 0;
  const mean = answers.reduce((a, b) => a + b, 0) / answers.length;
  return Math.round(mean * 10);
}

/// Computes deterministic scores from raw answers keyed by question id.
export function scoresFromRaw(rawAnswers: Record<string, number>): EnergyScores {
  const answersFor = (tag: string): number[] =>
    QUESTION_BANK.filter((q) => q.energy === tag)
      .map((q) => rawAnswers[q.id])
      .filter((v): v is number => v !== undefined);

  return {
    physical: scoreForAnswers(answersFor("physical")),
    emotional: scoreForAnswers(answersFor("emotional")),
    mental: scoreForAnswers(answersFor("mental")),
    spiritual: scoreForAnswers(answersFor("spiritual")),
    recovery: scoreForAnswers(answersFor("recovery")),
  };
}

/// Computes cumulative ±1 scores based on the previous day's scores.
/// Yes (rawAnswers["goal-{energy}"] === 10) → +1, No → −1, clamped to [0, 100].
/// When there is no previous entry (first ever check-in), each energy starts at 100.
export function cumulativeScores(
  rawAnswers: Record<string, number>,
  previousScores?: { physical: number; emotional: number; mental: number; spiritual: number },
): EnergyScores {
  const delta = (energy: Energy): number => (rawAnswers[`goal-${energy}`] === 10 ? 1 : -1);
  const base = (energy: Energy): number => previousScores?.[energy] ?? 100;
  const clamp = (v: number): number => Math.min(100, Math.max(0, v));

  return {
    physical: clamp(base("physical") + delta("physical")),
    emotional: clamp(base("emotional") + delta("emotional")),
    mental: clamp(base("mental") + delta("mental")),
    spiritual: clamp(base("spiritual") + delta("spiritual")),
    recovery: 0,
  };
}

// MARK: - Questions

export interface CheckInQuestion {
  id: string;
  /** physical | emotional | mental | spiritual | recovery */
  energy: string;
  text: string;
  lowLabel: string;
  highLabel: string;
}

export function questionEnergy(q: CheckInQuestion): Energy | undefined {
  return (ENERGIES as readonly string[]).includes(q.energy) ? (q.energy as Energy) : undefined;
}

/// Literature-grounded question bank (Section 9).
export const QUESTION_BANK: CheckInQuestion[] = [
  {
    id: "physical-1",
    energy: "physical",
    text: "How physically rested and energized do you feel right now?",
    lowLabel: "Depleted",
    highLabel: "Charged",
  },
  {
    id: "physical-2",
    energy: "physical",
    text: "Did you move your body and take real breaks today (pausing roughly every 90–120 min)?",
    lowLabel: "Not at all",
    highLabel: "Consistently",
  },
  {
    id: "emotional-1",
    energy: "emotional",
    text: "How positive vs. fear- or deficit-driven have your emotions been today?",
    lowLabel: "Toxic / anxious",
    highLabel: "Positive / calm",
  },
  {
    id: "emotional-2",
    energy: "emotional",
    text: "Could you summon positive emotion under stress today?",
    lowLabel: "Reactive",
    highLabel: "Steady",
  },
  {
    id: "mental-1",
    energy: "mental",
    text: "How well could you sustain focus without constant digital interruption?",
    lowLabel: "Scattered",
    highLabel: "Deep focus",
  },
  {
    id: "mental-2",
    energy: "mental",
    text: "Did you move flexibly between broad and narrow focus, with realistic optimism?",
    lowLabel: "Stuck",
    highLabel: "Fluid",
  },
  {
    id: "spiritual-1",
    energy: "spiritual",
    text: "How connected did today feel to your deeper purpose and values?",
    lowLabel: "Disconnected",
    highLabel: "Fully aligned",
  },
  {
    id: "spiritual-2",
    energy: "spiritual",
    text: "Did your actions today reflect what matters most to you?",
    lowLabel: "Off-course",
    highLabel: "On-purpose",
  },
  {
    id: "recovery-1",
    energy: "recovery",
    text: "How well did you balance effort (expenditure) with renewal (recovery)?",
    lowLabel: "All spend, no rest",
    highLabel: "Well-oscillated",
  },
];

/// Picks a daily set: one per energy (no recovery), weighting toward the
/// weakest energy from recent entries (surfacing its second question to vary).
export function dailySet(recent: { bottleneck: string }[]): CheckInQuestion[] {
  const weakest = recent.length > 0 ? recent[0].bottleneck : undefined;
  const picked: CheckInQuestion[] = [];

  for (const energy of ENERGIES) {
    const candidates = QUESTION_BANK.filter((q) => q.energy === energy);
    if (candidates.length === 0) continue;
    if (energy === weakest && candidates.length > 1) {
      const idx = recent.length % candidates.length;
      picked.push(candidates[idx]);
    } else {
      picked.push(candidates[0]);
    }
  }

  return picked;
}

/// Generates 4 Yes/No check-in questions directly from the user's saved ritual
/// goals (one per energy). Falls back to a generic phrasing when a goal is empty.
export function goalQuestions(profile: {
  goalPhysical: string;
  goalEmotional: string;
  goalMental: string;
  goalSpiritual: string;
} | undefined): CheckInQuestion[] {
  function makeQuestion(energy: Energy, goal: string): CheckInQuestion {
    const goalText = goal.trim();
    const text = goalText
      ? `Did you ${goalText} today?`
      : `Did you do your ${ENERGY_TITLE[energy].toLowerCase()} ritual today?`;
    return { id: `goal-${energy}`, energy, text, lowLabel: "", highLabel: "" };
  }

  if (!profile) {
    return ENERGIES.map((e) => makeQuestion(e, ""));
  }

  return [
    makeQuestion("physical", profile.goalPhysical),
    makeQuestion("emotional", profile.goalEmotional),
    makeQuestion("mental", profile.goalMental),
    makeQuestion("spiritual", profile.goalSpiritual),
  ];
}
