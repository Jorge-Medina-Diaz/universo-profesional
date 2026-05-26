import { renderHook } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { usePullToRefresh } from "@/shared/usePullToRefresh";

describe("usePullToRefresh", () => {
  it("returns initial state (not pulling, zero progress)", () => {
    const onRefresh = vi.fn();
    const { result } = renderHook(() => usePullToRefresh(onRefresh));
    expect(result.current.pulling).toBe(false);
    expect(result.current.progress).toBe(0);
  });

  it("does nothing when disabled", () => {
    const onRefresh = vi.fn();
    const { result } = renderHook(() => usePullToRefresh(onRefresh, false));
    expect(result.current.pulling).toBe(false);
  });
});
