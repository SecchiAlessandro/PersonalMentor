// Port of Store/EnergyStore.swift — upsert-today, queries, mock seeding, export.
// Async because IndexedDB is async; views consume these via hooks (useStore.ts).

import {
  db,
  DEFAULT_PURPOSE,
  startOfDay,
  startOfToday,
  type EnergyEntry,
  type UserProfile,
} from "./db";
import {
  balance,
  bottleneck,
  type EnergyScores,
} from "../models/energy";
import { coachingFor } from "../coach/ruleBasedCoach";

// MARK: - Profile

export async function currentProfile(): Promise<UserProfile | undefined> {
  return db.profiles.orderBy("createdAt").first();
}

export async function ensureProfile(): Promise<UserProfile> {
  const existing = await currentProfile();
  if (existing) return existing;
  const profile: UserProfile = {
    purpose: DEFAULT_PURPOSE,
    goalPhysical: "",
    goalEmotional: "",
    goalMental: "",
    goalSpiritual: "",
    createdAt: Date.now(),
    coachEnabled: false,
  };
  const id = await db.profiles.add(profile);
  return { ...profile, id };
}

export async function updateProfile(patch: Partial<UserProfile>): Promise<void> {
  const profile = await ensureProfile();
  await db.profiles.update(profile.id!, patch);
}

export async function hasCompletedOnboarding(): Promise<boolean> {
  return (await db.profiles.count()) > 0;
}

// MARK: - Entries

export async function allEntries(): Promise<EnergyEntry[]> {
  // Most-recent first.
  return db.entries.orderBy("day").reverse().toArray();
}

export async function recentEntries(limit = 30): Promise<EnergyEntry[]> {
  return db.entries.orderBy("day").reverse().limit(limit).toArray();
}

/// Ascending by day, on/after `since`.
export async function entriesSince(since: number): Promise<EnergyEntry[]> {
  const start = startOfDay(since);
  return db.entries.where("day").aboveOrEqual(start).sortBy("day");
}

export async function todaysEntry(): Promise<EnergyEntry | undefined> {
  return db.entries.get(startOfToday());
}

/// Returns the most recent entry strictly before today (used as the base for
/// cumulative ±1 scoring). Returns undefined when there is no prior history.
export async function previousEntry(): Promise<EnergyEntry | undefined> {
  const today = startOfToday();
  return db.entries
    .where("day")
    .below(today)
    .reverse()
    .first();
}

export async function entryOn(day: number): Promise<EnergyEntry | undefined> {
  return db.entries.get(startOfDay(day));
}

export interface UpsertInput {
  day?: number;
  scores: EnergyScores;
  coaching: string;
  ritualNudge: string;
  coachSource?: "ai" | "rule";
  rawAnswers: Record<string, number>;
  note?: string;
}

/// Upserts one entry for the given day (default: today). Enforces one per day.
export async function upsert(input: UpsertInput): Promise<EnergyEntry> {
  const day = startOfDay(input.day ?? startOfToday());
  const existing = await db.entries.get(day);
  const entry: EnergyEntry = {
    day,
    physical: input.scores.physical,
    emotional: input.scores.emotional,
    mental: input.scores.mental,
    spiritual: input.scores.spiritual,
    recovery: input.scores.recovery,
    bottleneck: bottleneck(input.scores),
    coaching: input.coaching,
    ritualNudge: input.ritualNudge,
    coachSource: input.coachSource,
    note: input.note,
    rawAnswers: input.rawAnswers,
    createdAt: existing?.createdAt ?? Date.now(),
  };
  await db.entries.put(entry);
  return entry;
}

export async function deleteEntry(day: number): Promise<void> {
  await db.entries.delete(startOfDay(day));
}

// MARK: - Mock seeding (Milestone 1/2)

/// Seeds N days of plausible mock entries if the store is empty.
export async function seedMockDataIfEmpty(days = 21): Promise<void> {
  if ((await db.entries.count()) > 0) return;

  const rows: EnergyEntry[] = [];
  for (let offset = days - 1; offset >= 0; offset--) {
    const d = new Date();
    d.setDate(d.getDate() - offset);
    const day = startOfDay(d);
    const phase = days - offset;

    const wave = (base: number, amp: number, shift: number): number => {
      const v = base + amp * Math.sin((phase + shift) / 3.0);
      return Math.min(100, Math.max(0, Math.round(v)));
    };

    const scores: EnergyScores = {
      physical: wave(62, 18, 0),
      emotional: wave(58, 22, 1.5),
      mental: wave(66, 16, 3),
      spiritual: wave(54, 20, 4.5),
      recovery: wave(60, 25, 2),
    };
    const result = coachingFor(undefined, scores, bottleneck(scores));
    rows.push({
      day,
      physical: scores.physical,
      emotional: scores.emotional,
      mental: scores.mental,
      spiritual: scores.spiritual,
      recovery: scores.recovery,
      bottleneck: bottleneck(scores),
      coaching: result.coaching,
      ritualNudge: result.ritualNudge,
      rawAnswers: {},
      createdAt: day,
    });
  }
  await db.entries.bulkPut(rows);
}

// MARK: - Export (Milestone 4)

interface ExportRow {
  date: string;
  physical: number;
  emotional: number;
  mental: number;
  spiritual: number;
  recovery: number;
  balance: number;
  bottleneck: string;
  coaching: string;
  ritualNudge: string;
  note: string | null;
  answers: Record<string, number>;
}

export async function exportJSON(): Promise<string> {
  const entries = (await allEntries()).sort((a, b) => a.day - b.day);
  const payload: ExportRow[] = entries.map((e) => ({
    date: new Date(e.day).toISOString(),
    physical: e.physical,
    emotional: e.emotional,
    mental: e.mental,
    spiritual: e.spiritual,
    recovery: e.recovery,
    balance: balance(e),
    bottleneck: e.bottleneck,
    coaching: e.coaching,
    ritualNudge: e.ritualNudge,
    note: e.note ?? null,
    answers: e.rawAnswers,
  }));
  return JSON.stringify(payload, null, 2);
}

export async function exportCSV(): Promise<string> {
  const entries = (await allEntries()).sort((a, b) => a.day - b.day);
  const lines = [
    "date,physical,emotional,mental,spiritual,recovery,balance,bottleneck,note",
  ];
  for (const e of entries) {
    const note = (e.note ?? "").replace(/"/g, '""');
    const fields = [
      new Date(e.day).toISOString(),
      `${e.physical}`,
      `${e.emotional}`,
      `${e.mental}`,
      `${e.spiritual}`,
      `${e.recovery}`,
      `${balance(e)}`,
      e.bottleneck,
      `"${note}"`,
    ];
    lines.push(fields.join(","));
  }
  return lines.join("\n");
}
