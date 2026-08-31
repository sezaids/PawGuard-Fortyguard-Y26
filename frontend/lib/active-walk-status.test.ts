import { describe, expect, it } from "vitest";
import { isActiveWalkStatus } from "./active-walk-status";

const completeStatus = {
  heat_risk: { score: 24, status: "Low", recommendation: "A cautious estimate." },
  surface_risk: { score: 12, level: "Low", reason: "Grass is cooler.", surface: "grass" },
  recommended_duration_minutes: 30,
  reminders: ["Offer water."],
  caution: "End early if your dog is uncomfortable.",
  disclaimer: "Planning guidance only.",
};

describe("Active Walk status validation", () => {
  it("accepts a complete deterministic status response", () => {
    expect(isActiveWalkStatus(completeStatus)).toBe(true);
  });

  it("rejects an incomplete response before the page can read nested scores", () => {
    expect(isActiveWalkStatus({ heat_risk: { status: "Low" } })).toBe(false);
    expect(isActiveWalkStatus({ ...completeStatus, surface_risk: undefined })).toBe(false);
  });

  it("rejects malformed score values instead of rendering them as risk estimates", () => {
    expect(isActiveWalkStatus({ ...completeStatus, heat_risk: { ...completeStatus.heat_risk, score: null } })).toBe(false);
  });
});
