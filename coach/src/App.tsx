// Routes between onboarding and the main three-tab shell (Section 6):
// Today · History · Settings. Port of RootView + MainTabView in
// FullEngagementApp.swift.

import { useState } from "react";
import { useHasOnboarded } from "./store/useStore";
import { Dashboard } from "./views/Dashboard";
import { History } from "./views/History";
import { Settings } from "./views/Settings";
import { Onboarding } from "./views/Onboarding";

type Tab = "today" | "history" | "settings";

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "today", label: "Today", icon: "◴" },
  { id: "history", label: "History", icon: "📈" },
  { id: "settings", label: "Settings", icon: "⚙️" },
];

export default function App() {
  const onboarded = useHasOnboarded();
  const [tab, setTab] = useState<Tab>("today");

  const todayShort = new Date().toLocaleDateString(undefined, { month: "short", day: "numeric" });

  // Start empty — the wheel and charts populate from the user's own check-ins.
  if (onboarded === undefined) {
    return <div className="min-h-screen bg-canvas" />;
  }

  if (!onboarded) {
    return <Onboarding onComplete={() => setTab("today")} />;
  }

  return (
    <div className="min-h-screen bg-canvas pb-20">
      {tab === "today" && <Dashboard />}
      {tab === "history" && <History />}
      {tab === "settings" && <Settings />}

      {/* Bottom tab bar */}
      <nav
        className="fixed inset-x-0 bottom-0 z-40 flex justify-around border-t pt-2 pb-6"
        style={{ background: "var(--surface)", borderColor: "var(--hairline)" }}
      >
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className="flex flex-col items-center gap-0.5 px-6 text-[11px] font-medium"
            style={{ color: tab === t.id ? "var(--color-accent)" : "var(--text-secondary)" }}
          >
            <span className="text-[18px] leading-none">{t.icon}</span>
            {t.label}
            {t.id === "today" && (
              <span className="text-[10px] font-normal opacity-70">{todayShort}</span>
            )}
          </button>
        ))}
      </nav>
    </div>
  );
}
