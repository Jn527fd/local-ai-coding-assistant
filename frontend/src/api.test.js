import { afterEach, describe, expect, it, vi } from "vitest";

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body),
  };
}

async function importApiForTest() {
  vi.resetModules();
  vi.stubGlobal("location", {
    protocol: "http:",
    hostname: "192.168.1.204",
  });

  return import("./api.js");
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api login", () => {
  it("verifies the cookie-backed session before resolving", async () => {
    const calls = [];
    vi.stubGlobal("fetch", async (url, options) => {
      calls.push({ url, options });
      if (url.endsWith("/auth/login")) {
        return jsonResponse({ username: "chuy" });
      }
      if (url.endsWith("/auth/me")) {
        return jsonResponse({ username: "chuy" });
      }
      return jsonResponse({ detail: "Unexpected request." }, 500);
    });

    const { API_BASE_URL, login } = await importApiForTest();
    const session = await login("chuy", "password");

    expect(API_BASE_URL).toBe("http://192.168.1.204:8000");
    expect(session).toEqual({ username: "chuy" });
    expect(calls.map((call) => call.url)).toEqual([
      "http://192.168.1.204:8000/auth/login",
      "http://192.168.1.204:8000/auth/me",
    ]);
    expect(calls[0].options.credentials).toBe("include");
    expect(calls[1].options.credentials).toBe("include");
  });

  it("fails clearly when the session cookie is not usable", async () => {
    vi.stubGlobal("fetch", async (url) => {
      if (url.endsWith("/auth/login")) {
        return jsonResponse({ username: "chuy" });
      }
      if (url.endsWith("/auth/me")) {
        return jsonResponse({ detail: "Login required." }, 401);
      }
      return jsonResponse({ detail: "Unexpected request." }, 500);
    });

    const { login } = await importApiForTest();

    await expect(login("chuy", "password")).rejects.toThrow(
      /browser session cookie could not be verified/,
    );
  });
});
