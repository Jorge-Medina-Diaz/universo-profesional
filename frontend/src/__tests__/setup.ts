import { beforeAll, afterAll, afterEach, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import { server } from "./mocks/server";

// jsdom does not implement IntersectionObserver (used by framer-motion / motion)
vi.stubGlobal(
  "IntersectionObserver",
  class {
    observe = vi.fn();
    disconnect = vi.fn();
    unobserve = vi.fn();
    takeRecords = vi.fn().mockReturnValue([]);
  }
);

vi.stubGlobal(
  "matchMedia",
  vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }))
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
