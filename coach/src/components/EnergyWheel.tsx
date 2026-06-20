// The signature UI (Section 5) — one circle, four quadrants filling radially
// from the center, plus a center hub with an oscillation glyph reflecting the
// recovery score. Port of Views/Today/EnergyWheel.swift + QuadrantShape.swift.

import { useEffect, useState } from "react";
import { ENERGIES, ENERGY_TITLE, type Energy, type EnergyScores } from "../models/energy";
import { energyHex, CENTER_ARROWS } from "../theme/theme";

const VB = 200; // viewBox size
const C = VB / 2; // center
const MAX_R = 98; // outer radius

// Angle convention matches the Swift version: screen coords (y down),
// 0° = right, increasing clockwise.
const QUADRANT_ANGLES: Record<Energy, [number, number]> = {
  spiritual: [0, 90], // bottom-right
  emotional: [90, 180], // bottom-left
  physical: [180, 270], // top-left
  mental: [270, 360], // top-right
};

function rad(deg: number): number {
  return (deg * Math.PI) / 180;
}

/// Full-radius pie wedge for a quadrant. The radial fill is produced by scaling
/// this path about the center, so we always draw it at MAX_R.
function wedgePath(start: number, end: number): string {
  const x1 = C + MAX_R * Math.cos(rad(start));
  const y1 = C + MAX_R * Math.sin(rad(start));
  const x2 = C + MAX_R * Math.cos(rad(end));
  const y2 = C + MAX_R * Math.sin(rad(end));
  // 90° arc, swept clockwise (sweep flag = 1 in screen coords).
  return `M ${C} ${C} L ${x1} ${y1} A ${MAX_R} ${MAX_R} 0 0 1 ${x2} ${y2} Z`;
}

function labelPos(energy: Energy): { x: number; y: number } {
  const [s, e] = QUADRANT_ANGLES[energy];
  const mid = rad((s + e) / 2);
  const r = 62; // ~0.62 of the radius, matching the Swift placement
  return { x: C + r * Math.cos(mid), y: C + r * Math.sin(mid) };
}

export function EnergyWheel({
  scores,
  onSelect,
}: {
  scores: EnergyScores;
  onSelect: (energy: Energy) => void;
}) {
  const [appeared, setAppeared] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setAppeared(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const bal = Math.max(
    0,
    100 -
      (Math.max(scores.physical, scores.emotional, scores.mental, scores.spiritual) -
        Math.min(scores.physical, scores.emotional, scores.mental, scores.spiritual)),
  );

  return (
    <svg viewBox={`0 0 ${VB} ${VB}`} className="mx-auto block w-full max-w-[360px]" role="group">
      {ENERGIES.map((energy) => {
        const [start, end] = QUADRANT_ANGLES[energy];
        const d = wedgePath(start, end);
        const color = energyHex(energy);
        const k = appeared ? scores[energy] / 100 : 0;
        const pos = labelPos(energy);
        return (
          <g key={energy}>
            {/* Faint full-quadrant track (100% boundary) + click target. */}
            <path
              d={d}
              fill={color}
              fillOpacity={0.16}
              style={{ cursor: "pointer" }}
              onClick={() => onSelect(energy)}
              role="button"
              aria-label={`${ENERGY_TITLE[energy]} energy, ${scores[energy]} percent`}
            />
            {/* Radial fill: full wedge scaled about the center by the score. */}
            <path
              d={d}
              fill={color}
              fillOpacity={0.9}
              style={{
                transform: `scale(${k})`,
                transformOrigin: `${C}px ${C}px`,
                transition: "transform 1s cubic-bezier(0.22, 1, 0.36, 1)",
                pointerEvents: "none",
              }}
            />
            {/* Label at the quadrant's angular midpoint. */}
            <text
              x={pos.x}
              y={pos.y}
              textAnchor="middle"
              style={{ pointerEvents: "none" }}
              fill="#ffffff"
            >
              <tspan
                x={pos.x}
                dy="-2"
                fontSize="9"
                fontWeight={700}
                letterSpacing="0.5"
                style={{ filter: "drop-shadow(0 1px 3px rgba(0,0,0,0.25))" }}
              >
                {ENERGY_TITLE[energy].toUpperCase()}
              </tspan>
              <tspan
                x={pos.x}
                dy="16"
                fontSize="16"
                fontWeight={600}
                fontFamily="ui-serif, Georgia, serif"
                style={{ filter: "drop-shadow(0 1px 3px rgba(0,0,0,0.25))" }}
              >
                {scores[energy]}
              </tspan>
            </text>
          </g>
        );
      })}

      {/* Dividing lines for crispness. */}
      <line x1={C} y1={C - MAX_R} x2={C} y2={C + MAX_R} stroke="#fff" strokeOpacity={0.22} strokeWidth={1.5} />
      <line x1={C - MAX_R} y1={C} x2={C + MAX_R} y2={C} stroke="#fff" strokeOpacity={0.22} strokeWidth={1.5} />

      <CenterHub recovery={scores.recovery} balance={bal} />
    </svg>
  );
}

/// Center hub: a circular surface, the balance number, and an oscillation glyph
/// whose clarity reflects recovery (and spins when recovery is high).
function CenterHub({ recovery, balance }: { recovery: number; balance: number }) {
  const HUB_R = 26;
  const clarity = 0.3 + 0.7 * (recovery / 100);
  const spinning = recovery > 60;

  // Material "autorenew" glyph (24×24), centered at the hub.
  const glyph =
    "M12 6v3l4-4-4-4v3c-4.42 0-8 3.58-8 8 0 1.57.46 3.03 1.24 4.26L6.7 14.8c-.45-.83-.7-1.79-.7-2.8 0-3.31 2.69-6 6-6zm6.76 1.74L17.3 9.2c.44.84.7 1.79.7 2.8 0 3.31-2.69 6-6 6v-3l-4 4 4 4v-3c4.42 0 8-3.58 8-8 0-1.57-.46-3.03-1.24-4.26z";

  return (
    <g aria-label={`Recovery ${recovery} percent, balance ${balance}`}>
      <circle cx={C} cy={C} r={HUB_R} fill="var(--surface)" style={{ filter: "drop-shadow(0 3px 8px rgba(0,0,0,0.2))" }} />
      <g
        style={{
          transformOrigin: `${C}px ${C}px`,
          animation: spinning ? "fe-spin 8s linear infinite" : "none",
        }}
      >
        <path d={glyph} transform={`translate(${C - 12}, ${C - 12})`} fill={CENTER_ARROWS} fillOpacity={clarity} />
      </g>
      <text x={C} y={C} textAnchor="middle" fill="var(--text-primary)">
        <tspan x={C} dy="2" fontSize="14" fontWeight={700} fontFamily="ui-serif, Georgia, serif">
          {balance}
        </tspan>
        <tspan x={C} dy="9" fontSize="6" fontWeight={600} fill="var(--text-secondary)">
          balance
        </tspan>
      </text>
    </g>
  );
}
