type IconProps = { name: string; className?: string };

const glyphs: Record<string, string> = {
  Dashboard: "⌂", "My Dogs": "♧", "Active Walk": "◉", "Walk Planner": "◷", "Route Planner": "↝", "Daily Schedule": "☷", "Walk Match": "♞", "Heat Map": "◉",
  Safety: "♢", History: "↶", Settings: "⚙", Assistant: "✦",
};

export function Icon({ name, className = "" }: IconProps) {
  return <span aria-hidden="true" className={`inline-flex w-5 justify-center text-lg leading-none ${className}`}>{glyphs[name] ?? "•"}</span>;
}
