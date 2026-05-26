import { http, HttpResponse } from "msw";

export const handlers = [
  http.post("*/api/v1/auth/register", () => {
    return HttpResponse.json({
      user_id: "user-123",
      email: "test@test.com",
      verification_link: "http://test/#/auth/verify?token=verify-token-123",
    });
  }),

  http.post("*/api/v1/auth/login", () => {
    return HttpResponse.json({
      access_token: "access-token-123",
      refresh_token: "refresh-token-123",
      user_id: "user-123",
      email: "test@test.com",
    });
  }),

  http.get("*/api/v1/users/me", () => {
    return HttpResponse.json({
      user_id: "user-123",
      email: "test@test.com",
      display_name: "Test User",
      locale: "es-ES",
      email_verified: true,
      mfa_enabled: false,
      created_at: "2024-01-01T00:00:00Z",
      tier: "free",
    });
  }),

  http.get("*/api/v1/integrations/linkedin/authorize", () => {
    return HttpResponse.json({ configured: false });
  }),

  http.post("*/api/v1/universe/header", () => {
    return HttpResponse.json({ ok: true });
  }),

  http.post("*/api/v1/import/linkedin", async ({ request }) => {
    const form = await request.formData();
    void form.get("file");
    return HttpResponse.json({
      experiences: 3,
      educations: 2,
      skills: 5,
    });
  }),
];
