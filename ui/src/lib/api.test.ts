import { resolveApiUrl } from "./api";

describe("resolveApiUrl", () => {
  const originalWindow = globalThis.window;

  afterEach(() => {
    vi.unstubAllEnvs();
    Object.defineProperty(globalThis, "window", {
      configurable: true,
      value: originalWindow
    });
  });

  it("uses relative API paths in the browser", () => {
    expect(resolveApiUrl("/api/ui/health")).toBe("/api/ui/health");
  });

  it("uses API proxy target for server-side fetches", () => {
    vi.stubEnv("API_PROXY_TARGET", "http://127.0.0.1:8030");
    Object.defineProperty(globalThis, "window", {
      configurable: true,
      value: undefined
    });

    expect(resolveApiUrl("/api/ui/metrics/paper")).toBe(
      "http://127.0.0.1:8030/api/ui/metrics/paper"
    );
  });
});
