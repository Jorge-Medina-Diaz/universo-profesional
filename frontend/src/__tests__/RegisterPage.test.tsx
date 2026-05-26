import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { RegisterPage } from "@/pages/RegisterPage";
import { createTestWrapper } from "./test-utils";

const wrapper = createTestWrapper();

describe("RegisterPage", () => {
  beforeEach(() => {
    localStorage.clear();
    window.location.hash = "";
  });

  it("renders registration form fields", () => {
    render(<RegisterPage />, { wrapper });
    expect(screen.getByLabelText(/nombre/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument();
  });

  it("submits registration and auto-logs in when possible", async () => {
    render(<RegisterPage />, { wrapper });
    fireEvent.change(screen.getByLabelText(/nombre/i), { target: { value: "Test" } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "test@example.com" } });
    fireEvent.change(screen.getByLabelText(/contraseña/i), { target: { value: "S3cur3-Passw0rd!" } });
    fireEvent.click(screen.getByRole("button", { name: /crear cuenta/i }));

    await waitFor(() => {
      const stored = JSON.parse(localStorage.getItem("cvs-saas-auth") || "{}");
      expect(stored.accessToken).toBe("access-token-123");
    });
  });
});
