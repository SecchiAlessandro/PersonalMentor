// A tiny inline trend line for the energy detail sheet (port of the Sparkline in
// Views/Today/DashboardView.swift).

export function Sparkline({ values, color }: { values: number[]; color: string }) {
  const W = 300;
  const H = 60;
  if (values.length === 0) {
    return <svg viewBox={`0 0 ${W} ${H}`} className="h-[60px] w-full" />;
  }
  const maxV = Math.max(...values, 1);
  const count = Math.max(values.length - 1, 1);
  const points = values
    .map((v, i) => {
      const x = (W * i) / count;
      const y = H * (1 - v / maxV);
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="h-[60px] w-full">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={2.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
