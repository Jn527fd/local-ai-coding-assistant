import { describe, expect, it } from "vitest";

import { resolveApiBaseUrl } from "./apiBase.js";

describe("resolveApiBaseUrl", () => {
  it("uses the browser host when API base URL is auto", () => {
    const result = resolveApiBaseUrl("auto", {
      protocol: "http:",
      hostname: "192.168.1.204",
    });

    expect(result).toBe("http://192.168.1.204:8000");
  });

  it("rewrites loopback API URLs when the app is opened over the LAN", () => {
    const result = resolveApiBaseUrl("http://localhost:8000", {
      protocol: "http:",
      hostname: "192.168.1.204",
    });

    expect(result).toBe("http://192.168.1.204:8000");
  });

  it("keeps explicit non-loopback API URLs", () => {
    const result = resolveApiBaseUrl("http://192.168.1.50:8000/", {
      protocol: "http:",
      hostname: "192.168.1.204",
    });

    expect(result).toBe("http://192.168.1.50:8000");
  });
});
