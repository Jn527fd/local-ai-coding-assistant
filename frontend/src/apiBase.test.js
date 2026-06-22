import assert from "node:assert/strict";
import test from "node:test";

import { resolveApiBaseUrl } from "./apiBase.js";

test("uses the browser host when API base URL is auto", () => {
  const result = resolveApiBaseUrl("auto", {
    protocol: "http:",
    hostname: "192.168.1.204",
  });

  assert.equal(result, "http://192.168.1.204:8000");
});

test("rewrites loopback API URLs when the app is opened over the LAN", () => {
  const result = resolveApiBaseUrl("http://localhost:8000", {
    protocol: "http:",
    hostname: "192.168.1.204",
  });

  assert.equal(result, "http://192.168.1.204:8000");
});

test("keeps explicit non-loopback API URLs", () => {
  const result = resolveApiBaseUrl("http://192.168.1.50:8000/", {
    protocol: "http:",
    hostname: "192.168.1.204",
  });

  assert.equal(result, "http://192.168.1.50:8000");
});
