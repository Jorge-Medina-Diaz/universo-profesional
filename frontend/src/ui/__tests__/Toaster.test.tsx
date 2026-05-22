import { describe, it, expect } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { ToasterProvider, toast } from "../Toaster";

describe("Toaster", () => {
  it("shows a success toast when toast.success is called", async () => {
    render(
      <ToasterProvider>
        <div>app</div>
      </ToasterProvider>,
    );
    act(() => {
      toast.success("Guardado", "Todo ok");
    });
    expect(await screen.findByText("Guardado")).toBeTruthy();
    expect(screen.getByText("Todo ok")).toBeTruthy();
  });

  it("supports updating an existing toast", async () => {
    render(
      <ToasterProvider>
        <div>app</div>
      </ToasterProvider>,
    );
    let id: string | undefined;
    act(() => {
      id = toast.loading("Subiendo");
    });
    expect(await screen.findByText("Subiendo")).toBeTruthy();
    act(() => {
      toast.update(id!, { variant: "success", title: "Subido" });
    });
    expect(await screen.findByText("Subido")).toBeTruthy();
  });
});
