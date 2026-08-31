import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

describe("production API proxy", () => {
  it("keeps browser API traffic on the same-origin Render proxy", () => {
    const config = JSON.parse(readFileSync(resolve(process.cwd(), "vercel.json"), "utf8")) as {
      rewrites: Array<{ source: string; destination: string }>;
    };
    expect(config.rewrites).toEqual([
      {
        source: "/backend/:path*",
        destination: "https://pawguard-fortyguard-y26-api.onrender.com/:path*",
      },
    ]);
  });
});
