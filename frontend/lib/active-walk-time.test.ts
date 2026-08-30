import { describe, expect, it } from "vitest";
import { durationWarning, formatElapsed } from "./active-walk-time";

describe("active walk timing", () => {
  it("formats elapsed time", () => expect(formatElapsed(125)).toBe("02:05"));
  it("warns at the recommended duration", () => expect(durationWarning(900, 15)).toBe(true));
  it("warns immediately when no outdoor duration is recommended", () => expect(durationWarning(0, 0)).toBe(true));
});
