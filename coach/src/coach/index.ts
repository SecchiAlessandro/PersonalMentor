// Coach factory — returns the deterministic rule-based coaching. The optional
// on-device AI coach from the iOS app is intentionally omitted in this build;
// scoring and prose are always deterministic. Port of CoachFactory in
// Coach/CoachService.swift.

import type { EnergyScores } from "../models/energy";
import type { UserProfile } from "../store/db";
import { coachingFor, type CoachResult } from "./ruleBasedCoach";

export type CoachSource = "rule";
export interface ResolvedCoaching extends CoachResult {
  source: CoachSource;
}

export async function coachFor(
  profile: UserProfile | undefined,
  scores: EnergyScores,
  bottleneckRaw?: string,
  missedGoals: string[] = [],
): Promise<ResolvedCoaching> {
  return { ...coachingFor(profile, scores, bottleneckRaw, missedGoals), source: "rule" };
}

export { coachingFor };
export type { CoachResult };
