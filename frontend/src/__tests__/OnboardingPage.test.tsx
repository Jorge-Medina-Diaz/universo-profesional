import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { OnboardingPage } from "@/pages/OnboardingPage";
import { createTestWrapper } from "./test-utils";

const wrapper = createTestWrapper();

describe("OnboardingPage wizard", () => {
  it("starts at welcome step", () => {
    render(<OnboardingPage />, { wrapper });
    expect(screen.getByText(/bienvenido/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /empezar/i })).toBeInTheDocument();
  });

  it("advances through steps", async () => {
    render(<OnboardingPage />, { wrapper });
    fireEvent.click(screen.getByRole("button", { name: /empezar/i }));

    await waitFor(() => {
      expect(screen.getByText(/importar datos/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /continuar/i }));

    await waitFor(() => {
      expect(screen.getByText(/tu titular/i)).toBeInTheDocument();
    });
  });

  it("shows progress indicator", () => {
    render(<OnboardingPage />, { wrapper });
    expect(screen.getByText(/paso 1 de 7/i)).toBeInTheDocument();
  });
});
