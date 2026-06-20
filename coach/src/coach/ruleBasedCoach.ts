// Port of Coach/RuleBasedCoach.swift — the guaranteed, deterministic coaching
// path. Coaching now focuses on missed daily goals; if all goals were met it
// gives positive reinforcement. Pyramid / bottleneck logic is used as fallback
// when no goal information is available.

import {
  type Energy,
  type EnergyScores,
  ENERGY_TITLE,
  balance as computeBalance,
  bottleneck as computeBottleneck,
} from "../models/energy";
import type { UserProfile } from "../store/db";

export interface CoachResult {
  coaching: string;
  ritualNudge: string;
}

function goalFor(profile: UserProfile | undefined, energy: Energy): string {
  if (!profile) return "";
  switch (energy) {
    case "physical":
      return profile.goalPhysical;
    case "emotional":
      return profile.goalEmotional;
    case "mental":
      return profile.goalMental;
    case "spiritual":
      return profile.goalSpiritual;
  }
}

function renewalRitual(energy: Energy): string {
  switch (energy) {
    case "physical":
      return "A concrete renewal ritual: a 10-minute walk and lights-out at a fixed time tonight.";
    case "emotional":
      return "A concrete renewal ritual: three slow breaths and one gratitude note before bed.";
    case "mental":
      return "A concrete renewal ritual: one 90-minute focus block tomorrow, phone in another room.";
    case "spiritual":
      return "A concrete renewal ritual: five quiet minutes tomorrow on why today's work matters.";
  }
}

/// Returns ONLY prose + nudge. Scores are computed deterministically elsewhere.
/// `missedGoals` is a list of question texts for goals the user answered No to.
export function coachingFor(
  profile: UserProfile | undefined,
  scores: EnergyScores,
  bottleneckRaw?: string,
  missedGoals: string[] = [],
): CoachResult {
  // All goals met — celebrate and encourage consistency.
  if (missedGoals.length === 0) {
    return {
      coaching:
        "You checked every goal today — well done. Consistency is how rituals become automatic. " +
        "Keep protecting these habits tomorrow.",
      ritualNudge: "All four rituals done. Schedule them again for tomorrow.",
    };
  }

  // Some goals missed — focus only on those.
  const weakest = (bottleneckRaw as Energy) ?? computeBottleneck(scores);
  const bal = computeBalance(scores);

  const joinLabels = (labels: string[]): string => {
    if (labels.length === 1) return labels[0];
    return labels.slice(0, -1).join(", ") + " and " + labels[labels.length - 1];
  };

  let coaching: string;
  if (missedGoals.length === 1) {
    coaching =
      `You missed your ${missedGoals[0]} ritual today. ` +
      "Small misses are normal — what matters is getting back on track tomorrow.";
  } else {
    coaching =
      `You missed ${missedGoals.length} rituals today: ${joinLabels(missedGoals)}. ` +
      "Restore those first before pushing harder elsewhere.";
    if (bal < 50 && scores.physical < 50 && weakest === "physical") {
      coaching += " Your physical foundation is low — start there, because it caps everything above it.";
    }
  }

  const nudge =
    `Tomorrow: schedule the missed ritual${missedGoals.length > 1 ? "s" : ""} like an appointment. ` +
    renewalRitual(weakest);

  // Append goal text as an extra nudge if available.
  const goalText = goalFor(profile, weakest)?.trim();
  const ritualNudge = goalText ? `${nudge} Your ritual: ${goalText}` : nudge;

  return { coaching, ritualNudge };
}
