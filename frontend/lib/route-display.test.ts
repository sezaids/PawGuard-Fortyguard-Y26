import { describe, expect, it } from "vitest";
import { routeDistanceMiles, routeHeatLabel } from "./route-display";

describe("route display helpers", () => {
  it("formats provider route distance in miles", () => {
    expect(routeDistanceMiles(1609.344)).toBe("1.00");
  });

  it("does not invent a heat value when optimization is unavailable", () => {
    expect(routeHeatLabel(null)).toBe("Heat unavailable");
  });

  it("labels only the supplied relative heat index", () => {
    expect(routeHeatLabel(42)).toBe("Relative heat 42/100");
  });
});
