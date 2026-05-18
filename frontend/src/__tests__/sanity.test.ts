import { describe, expect, it } from "vitest";

describe("sanity", () => {
  it("environment is jsdom", () => {
    expect(typeof window).toBe("object");
  });
});
