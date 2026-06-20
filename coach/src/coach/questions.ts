// Daily check-in question preparation. Generates 4 Yes/No questions directly
// from the user's saved ritual goals (one per energy). The recovery question
// has been removed; answers are binary (Yes = 10, No = 0).

import { goalQuestions, type CheckInQuestion } from "../models/energy";
import type { UserProfile } from "../store/db";

/// Prepares the day's 4 goal-based Yes/No questions from the user's profile.
export async function prepareDailyQuestions(
  profile: UserProfile | undefined,
  _recent: unknown[],
): Promise<CheckInQuestion[]> {
  return goalQuestions(profile);
}
