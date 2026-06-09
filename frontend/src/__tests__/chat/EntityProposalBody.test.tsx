import { screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { entityRichBody } from "@/chat/components/EntityProposalBody";
import { renderWithProviders } from "../utils";

describe("entityRichBody", () => {
  it("renders a rich skill body with level bar, category and years", () => {
    const el = entityRichBody("skill", {
      name: "Python",
      level: "high",
      years: 5,
      category: "hard",
    });
    expect(el).not.toBeNull();
    renderWithProviders(el!);
    expect(screen.getByTestId("skill-body")).toBeInTheDocument();
    expect(screen.getByText("Alto")).toBeInTheDocument();
    expect(screen.getByText("Técnica")).toBeInTheDocument();
    expect(screen.getByText("5 años")).toBeInTheDocument();
  });

  it("renders a rich project body with tech chips, highlights, impact and url", () => {
    const el = entityRichBody("project", {
      name: "Pagos",
      description: "Plataforma de pagos",
      role: "Tech Lead",
      project_type: "work",
      tech_stack: ["React", "Stripe"],
      highlights: ["Escaló a 10k usuarios"],
      impact: "Redujo el churn 20%",
      url: "https://github.com/u/pagos",
    });
    expect(el).not.toBeNull();
    renderWithProviders(el!);
    expect(screen.getByTestId("project-body")).toBeInTheDocument();
    expect(screen.getByText("React")).toBeInTheDocument();
    expect(screen.getByText("Stripe")).toBeInTheDocument();
    expect(screen.getByText("Escaló a 10k usuarios")).toBeInTheDocument();
    expect(screen.getByText("Redujo el churn 20%")).toBeInTheDocument();
    expect(screen.getByText("Profesional")).toBeInTheDocument();
    expect(screen.getByText("github.com/u/pagos")).toBeInTheDocument();
  });

  it("returns null for a kind without a bespoke body (generic fallback)", () => {
    expect(entityRichBody("certification", { name: "AWS SAA" })).toBeNull();
  });

  it("returns null for a skill with no structured data (generic fallback)", () => {
    expect(entityRichBody("skill", { name: "Python" })).toBeNull();
  });
});
