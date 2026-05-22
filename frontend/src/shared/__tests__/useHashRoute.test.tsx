import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useHashRoute, getHashPath } from "../useHashRoute";

describe("useHashRoute", () => {
  beforeEach(() => {
    window.location.hash = "#/";
  });

  it("returns root by default", () => {
    expect(getHashPath()).toBe("/");
  });

  it("strips the leading # and query", () => {
    window.location.hash = "#/connections?connected=github";
    expect(getHashPath()).toBe("/connections");
  });

  it("updates on hashchange", () => {
    const { result } = renderHook(() => useHashRoute());
    expect(result.current).toBe("/");
    act(() => {
      window.location.hash = "#/universe";
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    expect(result.current).toBe("/universe");
  });
});
