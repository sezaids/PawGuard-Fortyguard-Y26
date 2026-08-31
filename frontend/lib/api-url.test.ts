import { describe, expect, it } from "vitest";

import { apiBaseUrl, apiEndpoint, middlewareApiEndpoint } from "./api-url";

describe("production API proxy paths", () => {
  it("keeps the Vercel proxy prefix and backend API version exactly once", () => {
    expect(apiEndpoint(apiBaseUrl("/backend"), "/auth/signup")).toBe("/backend/api/v1/auth/signup");
    expect(apiEndpoint(apiBaseUrl("/backend/"), "auth/login")).toBe("/backend/api/v1/auth/login");
  });

  it("turns a relative Vercel proxy path into a valid middleware fetch URL", () => {
    expect(middlewareApiEndpoint("/backend", "https://pawguard.example/signup")).toBe("https://pawguard.example/backend/api/v1/auth/me");
  });

  it("keeps an absolute local backend URL usable during development", () => {
    expect(middlewareApiEndpoint("http://localhost:8000", "http://localhost:3000/dogs")).toBe("http://localhost:8000/api/v1/auth/me");
  });
});
