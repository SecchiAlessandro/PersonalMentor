// Reusable design-system components — port of DesignSystem/Components.swift.

import type { ReactNode, CSSProperties } from "react";

/// A crafted card surface (coach card, detail rows, etc.).
export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-[22px] bg-surface p-[18px] ${className}`}
      style={{
        boxShadow: "0 6px 14px var(--card-shadow)",
        border: "1px solid var(--hairline)",
      }}
    >
      {children}
    </div>
  );
}

/// The primary call-to-action button.
export function PrimaryButton({
  title,
  icon,
  tint,
  disabled,
  onClick,
}: {
  title: string;
  icon?: ReactNode;
  tint?: string;
  disabled?: boolean;
  onClick?: () => void;
}) {
  const style: CSSProperties = { backgroundColor: tint ?? "var(--color-accent)" };
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      style={style}
      className="flex w-full items-center justify-center gap-2 rounded-[18px] py-4 text-[17px] font-semibold text-black transition-opacity disabled:opacity-50"
    >
      {icon}
      <span>{title}</span>
    </button>
  );
}

/// A small pill label (e.g. for the bottleneck energy).
export function PillLabel({ text, color }: { text: string; color: string }) {
  return (
    <span
      className="rounded-full px-3 py-1.5 text-[13px] font-semibold"
      style={{ backgroundColor: `color-mix(in srgb, ${color} 18%, transparent)`, color }}
    >
      {text}
    </span>
  );
}

/// A section header in the characterful serif.
export function SectionHeader({ title }: { title: string }) {
  return (
    <h2 className="font-display text-[22px] font-semibold text-primary">{title}</h2>
  );
}
