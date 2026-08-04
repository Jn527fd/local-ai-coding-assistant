import { afterAll, afterEach, beforeAll, describe, expect, it } from "vitest"
import { http, HttpResponse } from "msw"
import { setupServer } from "msw/node"
import { createApiClient } from "./client"
import { normalizeApiBaseUrl } from "."

const server = setupServer(
  http.post("http://api.test/conversations", async ({ request }) => {
    return HttpResponse.json(
      { id: "conversation-1", ...(await request.json()) as object },
      { status: 201 },
    )
  }),
  http.post("http://api.test/form", async ({ request }) => {
    return HttpResponse.json({
      contentType: request.headers.get("content-type"),
      csrf: request.headers.get("x-csrf-token"),
      authorization: request.headers.get("authorization"),
      body: Object.fromEntries(await request.formData()),
    })
  }),
  http.put("http://api.test/csrf", ({ request }) =>
    HttpResponse.json({
      csrf: request.headers.get("x-csrf-token"),
      credentials: request.credentials,
    }),
  ),
  http.get(
    "http://api.test/empty",
    () => new HttpResponse(null, { status: 204 }),
  ),
  http.get("http://api.test/failure", () =>
    HttpResponse.json({ message: "Backend unavailable" }, { status: 503 }),
  ),
  http.get("http://api.test/fastapi-detail", () =>
    HttpResponse.json({ detail: "Invalid username or password." }, {
      status: 401,
    }),
  ),
  http.get("http://api.test/fastapi-validation", () =>
    HttpResponse.json(
      {
        detail: [
          { loc: ["body", "message"], msg: "Field required" },
          {
            loc: ["body", "history", 0, "content"],
            msg: "String should have at least 1 character",
          },
        ],
      },
      { status: 422 },
    ),
  ),
)

beforeAll(() => server.listen({ onUnhandledRequest: "error" }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe("API client network boundary", () => {
  const client = createApiClient({
    baseUrl: "http://api.test",
    getAccessToken: () => "token",
    fetchImplementation: (...arguments_) => fetch(...arguments_),
  })

  it("serializes JSON through an MSW network handler", async () => {
    await expect(
      client.request("/conversations", {
        method: "POST",
        body: { title: "Hello" },
      }),
    ).resolves.toEqual({ id: "conversation-1", title: "Hello" })
  })

  it("normalizes HTTP errors", async () => {
    await expect(client.request("/failure")).rejects.toMatchObject({
      code: "server",
      status: 503,
      message: "Backend unavailable",
    })
  })

  it("returns undefined for empty responses", async () => {
    await expect(client.request("/empty")).resolves.toBeUndefined()
  })

  it("maps FastAPI detail strings", async () => {
    await expect(client.request("/fastapi-detail")).rejects.toMatchObject({
      code: "unauthorized",
      status: 401,
      message: "Invalid username or password.",
    })
  })

  it("maps FastAPI validation arrays", async () => {
    await expect(client.request("/fastapi-validation")).rejects.toMatchObject({
      code: "validation",
      status: 422,
      message:
        "message: Field required history.0.content: String should have at least 1 character",
    })
  })

  it("sends cookies credentials and CSRF headers on unsafe requests", async () => {
    document.cookie = "local_ai_csrf=csrf-123"

    await expect(
      client.request("/csrf", { method: "PUT", body: { ok: true } }),
    ).resolves.toEqual({
      csrf: "csrf-123",
      credentials: "include",
    })
  })

  it("sends multipart requests without overriding the browser content type", async () => {
    document.cookie = "local_ai_csrf=csrf-form"
    const formData = new FormData()
    formData.set("name", "notes.txt")

    await expect(
      client.request("/form", { method: "POST", formData }),
    ).resolves.toMatchObject({
      authorization: "Bearer token",
      csrf: "csrf-form",
      body: { name: "notes.txt" },
    })
  })
})

describe("API base URL configuration", () => {
  it("uses same-origin API calls for Docker auto mode", () => {
    expect(normalizeApiBaseUrl("auto")).toBe("")
    expect(normalizeApiBaseUrl(" AUTO ")).toBe("")
  })

  it("keeps explicit backend URLs and the development fallback", () => {
    expect(normalizeApiBaseUrl("http://localhost:8000")).toBe(
      "http://localhost:8000",
    )
    expect(normalizeApiBaseUrl(undefined)).toBe("/api")
  })
})
