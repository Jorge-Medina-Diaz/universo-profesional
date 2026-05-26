import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect } from "vitest";
import { OnboardingPage } from "@/pages/OnboardingPage";

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

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
