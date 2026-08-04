import { beforeEach, describe, expect, it } from "vitest"
import {
  API_KEY_STORAGE_KEY,
  createBrowserApiKeyStorage,
} from "./apiKeyStorage"

describe("API key storage boundary", () => {
  beforeEach(() => localStorage.clear())

  it("uses the current app storage key for compatibility", () => {
    const storage = createBrowserApiKeyStorage()
    storage.set("secret")

    expect(localStorage.getItem(API_KEY_STORAGE_KEY)).toBe("secret")
    expect(storage.get()).toBe("secret")
  })

  it("returns an empty key when no key is stored", () => {
    expect(createBrowserApiKeyStorage().get()).toBe("")
  })
})
