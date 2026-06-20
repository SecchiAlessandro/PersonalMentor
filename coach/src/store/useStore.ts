// Live-query React hooks over the Dexie store. Components read through these so
// the UI updates automatically when data changes (like @Query in SwiftData).

import { useLiveQuery } from "dexie-react-hooks";
import { db, startOfDay, startOfToday, type EnergyEntry, type Ritual, type UserProfile } from "./db";

export function useProfile(): UserProfile | undefined {
  return useLiveQuery(() => db.profiles.orderBy("createdAt").first());
}

/** undefined while loading; true/false once known. */
export function useHasOnboarded(): boolean | undefined {
  return useLiveQuery(async () => (await db.profiles.count()) > 0);
}

export function useTodaysEntry(): EnergyEntry | undefined {
  return useLiveQuery(() => db.entries.get(startOfToday()));
}

/** The most recent entry regardless of day — used to show last known scores. */
export function useLatestEntry(): EnergyEntry | undefined {
  return useLiveQuery(() => db.entries.orderBy("day").last());
}

/** Ascending by day, within the last `days` days (inclusive of today). */
export function useEntriesInRange(days: number): EnergyEntry[] | undefined {
  return useLiveQuery(() => {
    const d = new Date();
    d.setDate(d.getDate() - (days - 1));
    const since = startOfDay(d);
    return db.entries.where("day").aboveOrEqual(since).sortBy("day");
  }, [days]);
}

export function useRituals(): Ritual[] | undefined {
  return useLiveQuery(() => db.rituals.orderBy("createdAt").toArray());
}
