// JS-side color tokens — mirror DesignSystem/Theme.swift. Used where CSS
// utilities can't reach (SVG fills, Recharts series colors).

import type { Energy } from "../models/energy";

export const ENERGY_HEX: Record<Energy, string> = {
  physical: "#B25750", // dusty terracotta — top-left
  mental: "#8FB05A", // sage green — top-right
  emotional: "#4F96B5", // teal blue — bottom-left
  spiritual: "#7E5FA8", // muted violet — bottom-right
};

export const BALANCE_ACCENT = "#43D6B5";
export const CENTER_ARROWS = "#E6E2DE";

export function energyHex(energy: Energy): string {
  return ENERGY_HEX[energy];
}
