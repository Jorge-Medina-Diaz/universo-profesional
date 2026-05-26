import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { LoginPage } from "@/pages/LoginPage";
import { createTestWrapper } from "./test-utils";

const wrapper = createTestWrapper();

describe("LoginPage", () => {
  beforeEach(() => {
    localStorage.clear();
    window.location.hash = "";
  });

  it("renders email and password fields", () => {
    render(<LoginPage />, { wrapper });
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /entrar/i })).toBeInTheDocument();
  });

  it("submits form and stores tokens", async () => {
    render(<LoginPage />, { wrapper });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "test@example.com" } });
    fireEvent.change(screen.getByLabelText(/contraseña/i), { target: { value: "S3cur3-Passw0rd!" } });
    fireEvent.click(screen.getByRole("button", { name: /entrar/i }));

    await waitFor(() => {
      const stored = JSON.parse(localStorage.getItem("cvs-saas-auth") || "{}");
      expect(stored.accessToken).toBe("access-token-123");
      expect(stored.email).toBe("test@example.com");
    });
  });
});
