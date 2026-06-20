// IndexedDB schema (via Dexie) — the web equivalent of the SwiftData store.
// All data is on-device; there is no server (mirrors the iOS privacy model).

import Dexie, { type Table } from "dexie";

export const DEFAULT_PURPOSE =
  "Is the life I am living worth what I'm giving up to have it?";

/// Single profile per user (port of Models/UserProfile.swift).
export interface UserProfile {
  id?: number;
  purpose: string;
  goalPhysical: string;
  goalEmotional: string;
  goalMental: string;
  goalSpiritual: string;
  createdAt: number; // epoch ms
  coachEnabled: boolean; // on-device AI not yet ported on web — kept for parity
}

/// One check-in per calendar day (port of Models/EnergyEntry.swift).
/// `day` is the start-of-day epoch ms and is the unique key (one per day).
export interface EnergyEntry {
  day: number; // start-of-day epoch ms (primary key)
  physical: number; // 0…100
  emotional: number;
  mental: number;
  spiritual: number;
  recovery: number;
  bottleneck: string;
  coaching: string;
  ritualNudge: string;
  coachSource?: "ai" | "rule"; // which coach produced the prose
  note?: string;
  rawAnswers: Record<string, number>;
  createdAt: number;
}

/// Optional ritual tracking (port of Models/Ritual.swift).
export interface Ritual {
  id?: number;
  energy: string;
  text: string;
  active: boolean;
  streak: number;
  lastDone?: number;
  createdAt: number;
}

class FullEngagementDB extends Dexie {
  profiles!: Table<UserProfile, number>;
  entries!: Table<EnergyEntry, number>;
  rituals!: Table<Ritual, number>;

  constructor() {
    super("FullEngagement");
    this.version(1).stores({
      profiles: "++id, createdAt",
      entries: "day, createdAt",
      rituals: "++id, createdAt, energy",
    });
  }
}

export const db = new FullEngagementDB();

// MARK: - Date helpers (port of Date.startOfToday / startOfDay)

export function startOfDay(date: Date | number): number {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

export function startOfToday(): number {
  return startOfDay(new Date());
}
