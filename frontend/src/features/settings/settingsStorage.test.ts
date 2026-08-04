import { beforeEach, describe, expect, it } from "vitest"
import {
  DEFAULT_APP_SETTINGS,
  loadAppSettings,
  SETTINGS_STORAGE_KEY,
} from "./settingsStorage"

describe("settingsStorage", () => {
  beforeEach(() => localStorage.clear())

  it("falls back safely when stored settings are malformed", () => {
    localStorage.setItem(SETTINGS_STORAGE_KEY, "{not-json")
    expect(loadAppSettings()).toEqual(DEFAULT_APP_SETTINGS)
  })

  it("validates every stored setting before returning it", () => {
    localStorage.setItem(
      SETTINGS_STORAGE_KEY,
      JSON.stringify({
        theme: "neon",
        textSize: "huge",
        sendOnEnter: "yes",
        showMessageTimestamps: false,
        confirmBeforeDeleteChats: 0,
      }),
    )

    expect(loadAppSettings()).toEqual({
      ...DEFAULT_APP_SETTINGS,
      showMessageTimestamps: false,
    })
  })
})
