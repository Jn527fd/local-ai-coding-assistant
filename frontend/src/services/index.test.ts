import { describe, expect, it } from "vitest"
import { createApiClient } from "../api"
import { createAppServices, resolveUseMockApi } from "."

describe("application service selection", () => {
  it("keeps mock services as the default", () => {
    expect(resolveUseMockApi(undefined)).toBe(true)
    expect(resolveUseMockApi("true")).toBe(true)
    expect(resolveUseMockApi(true)).toBe(true)
  })

  it("selects HTTP services only when mock mode is explicitly false", () => {
    expect(resolveUseMockApi("false")).toBe(false)
    expect(resolveUseMockApi("FALSE")).toBe(false)
    expect(resolveUseMockApi(false)).toBe(false)
  })

  it("creates mock services with test control in mock mode", async () => {
    const selection = createAppServices({ useMockApi: true })
    selection.mockControl?.setLatency(0)

    await expect(
      selection.services.auth.signIn({ username: "test", password: "test" }),
    ).resolves.toMatchObject({ user: { username: "test" } })
  })

  it("creates HTTP services in HTTP mode", async () => {
    const selection = createAppServices({
      useMockApi: false,
      client: createApiClient({
        baseUrl: "http://api.test",
        fetchImplementation: async () =>
          Response.json({ username: "http-user" }),
      }),
    })

    expect(selection.mockControl).toBeNull()
    await expect(
      selection.services.auth.signIn({ username: "test", password: "test" }),
    ).resolves.toMatchObject({ user: { username: "http-user" } })
  })
})
