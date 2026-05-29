/**
 * Onboarding completion flag — per user, persisted in localStorage.
 *
 * The router's onboarding gate funnels users with an empty universe to
 * `#/onboarding`. Without a "done" marker that gate fires on *every*
 * navigation, so finishing onboarding (or skipping it) and heading to the
 * universe bounced the user straight back — the "Ir a mi universo" button
 * appeared dead. Once a user has explicitly completed or skipped onboarding we
 * record it here and the gate leaves them alone, even if their universe is
 * still empty (the universe page shows its own empty state).
 *
 * Scoped by user id so a different account on the same browser still gets
 * onboarded.
 */
const KEY = "cvs-saas-onboarding-done";

function readSet(): Set<string> {
  try {
    const arr = JSON.parse(localStorage.getItem(KEY) || "[]");
    return new Set(Array.isArray(arr) ? arr.map(String) : []);
  } catch {
    return new Set();
  }
}

export function markOnboardingComplete(userId: string | null): void {
  try {
    const set = readSet();
    set.add(userId ?? "anon");
    localStorage.setItem(KEY, JSON.stringify([...set]));
  } catch {
    /* ignore — a missing flag only means the user may see onboarding again */
  }
}

export function isOnboardingComplete(userId: string | null): boolean {
  return readSet().has(userId ?? "anon");
}
