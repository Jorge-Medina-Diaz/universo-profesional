/**
 * Tiny smoke tests for Button. Verifies variants render, loading state
 * disables, and click handlers wire through. Not exhaustive — just enough
 * to catch regressions in the primitive that the whole UI depends on.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Button } from "../Button";

describe("Button", () => {
  it("renders label", () => {
    render(<Button>Hola</Button>);
    expect(screen.getByRole("button", { name: "Hola" })).toBeTruthy();
  });

  it("fires onClick", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Click</Button>);
    fireEvent.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("disables and swallows clicks when loading", () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Guardando
      </Button>,
    );
    const btn = screen.getByRole("button");
    expect(btn.hasAttribute("disabled")).toBe(true);
    fireEvent.click(btn);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("supports variants without throwing", () => {
    const variants = ["primary", "secondary", "ghost", "outline", "danger"] as const;
    for (const v of variants) {
      const { unmount } = render(<Button variant={v}>{v}</Button>);
      expect(screen.getByRole("button", { name: v })).toBeTruthy();
      unmount();
    }
  });
});
