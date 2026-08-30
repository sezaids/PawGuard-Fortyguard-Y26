export function routeDistanceMiles(meters: number): string {
  return (meters / 1609.344).toFixed(2);
}

export function routeHeatLabel(exposure: number | null): string {
  return exposure === null ? "Heat unavailable" : `Relative heat ${exposure}/100`;
}
