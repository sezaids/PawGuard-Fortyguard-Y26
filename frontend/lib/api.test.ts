import { describe, expect, it } from "vitest";
import { apiErrorMessage } from "./api";

describe("API error messages", () => {
  it("uses a plain API detail", () => {
    expect(apiErrorMessage({ detail: "FortyGuard is still processing." })).toBe("FortyGuard is still processing.");
  });

  it("turns FastAPI structured validation details into readable text", () => {
    expect(apiErrorMessage({ detail: [{ msg: "Field required" }, { msg: "Must be a valid number" }] })).toBe("Field required Must be a valid number");
  });

  it("never renders an object as the user-facing message", () => {
    expect(apiErrorMessage({ detail: { code: "provider_error" } })).toBe("Something went wrong. Please try again.");
  });
});
