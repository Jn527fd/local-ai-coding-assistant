import assert from "node:assert/strict";
import test from "node:test";

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body),
  };
}

async function importApiForTest() {
  Object.defineProperty(globalThis, "location", {
    configurable: true,
    value: {
      protocol: "http:",
      hostname: "192.168.1.204",
    },
  });

  return import(`./api.js?test=${Date.now()}-${Math.random()}`);
}

test("login verifies the cookie-backed session before resolving", async () => {
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith("/auth/login")) {
      return jsonResponse({ username: "chuy" });
    }
    if (url.endsWith("/auth/me")) {
      return jsonResponse({ username: "chuy" });
    }
    return jsonResponse({ detail: "Unexpected request." }, 500);
  };

  const { API_BASE_URL, login } = await importApiForTest();
  const session = await login("chuy", "password");

  assert.equal(API_BASE_URL, "http://192.168.1.204:8000");
  assert.deepEqual(session, { username: "chuy" });
  assert.deepEqual(
    calls.map((call) => call.url),
    [
      "http://192.168.1.204:8000/auth/login",
      "http://192.168.1.204:8000/auth/me",
    ],
  );
  assert.equal(calls[0].options.credentials, "include");
  assert.equal(calls[1].options.credentials, "include");
});

test("login fails clearly when the session cookie is not usable", async () => {
  globalThis.fetch = async (url) => {
    if (url.endsWith("/auth/login")) {
      return jsonResponse({ username: "chuy" });
    }
    if (url.endsWith("/auth/me")) {
      return jsonResponse({ detail: "Login required." }, 401);
    }
    return jsonResponse({ detail: "Unexpected request." }, 500);
  };

  const { login } = await importApiForTest();

  await assert.rejects(
    () => login("chuy", "password"),
    /browser session cookie could not be verified/,
  );
});
