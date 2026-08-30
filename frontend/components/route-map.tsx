"use client";

type Position = [number, number];
type Route = { id: string; geometry: { type: string; coordinates: Position[] }; distance_meters: number; duration_seconds: number; estimated_walking_minutes: number; relative_heat_exposure: number | null; heat_optimized: boolean; explanation: string };
type Feature = { properties?: Record<string, unknown>; geometry?: { type?: string; coordinates?: unknown } };
const heatColors = ["#d9eee6", "#b7dcca", "#e6d373", "#ed9b57", "#d65740"];
function tileValue(properties: Record<string, unknown> | undefined) { const entry = Object.entries(properties ?? {}).find(([key, value]) => /temperature|tcm|value/i.test(key) && typeof value === "number"); return entry ? entry[1] as number : null; }
function rings(feature: Feature): Position[][] { const geometry = feature.geometry; if (!geometry?.coordinates) return []; return geometry.type === "Polygon" ? geometry.coordinates as Position[][] : geometry.type === "MultiPolygon" ? (geometry.coordinates as Position[][][]).flat() : []; }

export function RouteMap({ recommended, alternatives, heatmap, activeId, onSelect }: { recommended: Route; alternatives: Route[]; heatmap: Record<string, unknown> | null; activeId: string; onSelect: (id: string) => void }) {
  const routes = [recommended, ...alternatives]; const features = (Array.isArray(heatmap?.features) ? heatmap.features : []) as Feature[];
  const points = [...routes.flatMap(route => route.geometry.coordinates), ...features.flatMap(rings).flat()];
  if (!points.length) return null;
  const longs = points.map(point => point[0]); const lats = points.map(point => point[1]); const minLon = Math.min(...longs); const maxLon = Math.max(...longs); const minLat = Math.min(...lats); const maxLat = Math.max(...lats);
  const project = (point: Position) => `${((point[0] - minLon) / Math.max(maxLon - minLon, .00001)) * 100},${100 - ((point[1] - minLat) / Math.max(maxLat - minLat, .00001)) * 100}`;
  const values = features.map(feature => tileValue(feature.properties)).filter((value): value is number => value !== null); const color = (value: number | null) => { if (value === null || !values.length) return "#dfece7"; const index = Math.min(4, Math.floor(((value - Math.min(...values)) / Math.max(Math.max(...values) - Math.min(...values), .00001)) * 5)); return heatColors[index]; };
  return <div className="relative overflow-hidden rounded-2xl bg-[#edf3ef]"><svg viewBox="0 0 100 100" preserveAspectRatio="none" className="aspect-[1.25] w-full" role="img" aria-label="Walking route map with available FortyGuard heat tiles">{features.flatMap((feature, index) => rings(feature).map((ring, ringIndex) => <polygon key={`tile-${index}-${ringIndex}`} points={ring.map(project).join(" ")} fill={color(tileValue(feature.properties))} stroke="rgba(255,255,255,.5)" strokeWidth=".2" />))}{routes.map((route, index) => <polyline key={route.id} points={route.geometry.coordinates.map(project).join(" ")} fill="none" stroke={route.id === activeId ? "#183d36" : index === 0 ? "#47977e" : "#899995"} strokeWidth={route.id === activeId ? "2.3" : "1.1"} vectorEffect="non-scaling-stroke" className="cursor-pointer" onClick={() => onSelect(route.id)} />)}<circle cx={project(recommended.geometry.coordinates[0]).split(",")[0]} cy={project(recommended.geometry.coordinates[0]).split(",")[1]} r="2" fill="#183d36" /></svg><span className="absolute left-3 top-3 rounded-full bg-white/90 px-3 py-1 text-xs font-semibold text-ink">{heatmap ? "Available FortyGuard tile overlay" : "Walking routes"}</span></div>;
}
