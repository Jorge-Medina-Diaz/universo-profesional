import { screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ArtifactProposalCard } from "@/chat/cards/ArtifactProposalCard";
import { renderWithProviders } from "../utils";

describe("ArtifactProposalCard", () => {
  const createProps = () => ({
    initialType: "github_repo" as const,
    initialTitle: "My Repo",
    initialUrl: "https://github.com/user/repo",
    initialYear: 2024,
    initialDescription: "A cool repo",
    pending: false,
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
  });

  let baseProps = createProps();

  beforeEach(() => {
    baseProps = createProps();
  });

  it("renders with correct entity type label", () => {
    renderWithProviders(<ArtifactProposalCard {...baseProps} />);
    expect(screen.getByText("Añadir al portfolio")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Repo/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Blog/i })).toBeInTheDocument();
  });

  it("confirm button calls onConfirm with payload", () => {
    renderWithProviders(<ArtifactProposalCard {...baseProps} />);
    fireEvent.click(screen.getByRole("button", { name: /Guardar/i }));
    expect(baseProps.onConfirm).toHaveBeenCalledTimes(1);
    const payload = baseProps.onConfirm.mock.calls[0][0];
    expect(payload.title).toBe("My Repo");
    expect(payload.url).toBe("https://github.com/user/repo");
    expect(payload.type).toBe("github_repo");
  });

  it("cancel button calls onCancel", () => {
    renderWithProviders(<ArtifactProposalCard {...baseProps} />);
    fireEvent.click(screen.getByRole("button", { name: /Descartar/i }));
    expect(baseProps.onCancel).toHaveBeenCalledTimes(1);
  });

  it("edit mode updates inline form values and reflects in confirm payload", () => {
    renderWithProviders(<ArtifactProposalCard {...baseProps} />);

    // Change title
    const titleInput = screen.getByPlaceholderText(/RAG patterns/i);
    fireEvent.change(titleInput, { target: { value: "Updated Title" } });

    // Change URL
    const urlInput = screen.getByPlaceholderText(/github.com/i);
    fireEvent.change(urlInput, { target: { value: "https://github.com/user/updated" } });

    // Select a different type
    fireEvent.click(screen.getByRole("button", { name: /Blog/i }));

    // Confirm
    fireEvent.click(screen.getByRole("button", { name: /Guardar/i }));

    expect(baseProps.onConfirm).toHaveBeenCalledTimes(1);
    const payload = baseProps.onConfirm.mock.calls[0][0];
    expect(payload.title).toBe("Updated Title");
    expect(payload.url).toBe("https://github.com/user/updated");
    expect(payload.type).toBe("blog_post");
  });

  it("disables confirm when title is empty", () => {
    renderWithProviders(<ArtifactProposalCard {...baseProps} initialTitle="" />);
    const confirmBtn = screen.getByRole("button", { name: /Guardar/i });
    expect(confirmBtn).toBeDisabled();
  });

  it("shows URL validation error for invalid URL", () => {
    renderWithProviders(<ArtifactProposalCard {...baseProps} />);
    const urlInput = screen.getByPlaceholderText(/github.com/i);
    fireEvent.change(urlInput, { target: { value: "not-a-url" } });
    expect(screen.getByText(/URL no válida/i)).toBeInTheDocument();
  });
});
