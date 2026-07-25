import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { formatConversationTime } from "./formatConversationTime"

describe("formatConversationTime", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] })
    vi.setSystemTime(new Date("2026-07-18T12:00:00Z"))
  })
  afterEach(() => vi.useRealTimers())

  it.each([
    ["2026-07-18T11:59:45Z", "Now"],
    ["2026-07-18T11:55:00Z", "5 minutes ago"],
    ["2026-07-18T10:00:00Z", "2 hours ago"],
    ["2026-07-16T12:00:00Z", "2 days ago"],
  ])("formats %s as %s", (value, expected) => {
    expect(formatConversationTime(value)).toBe(expected)
  })

  it("handles invalid and older timestamps", () => {
    expect(formatConversationTime("invalid")).toBe("Unknown")
    expect(formatConversationTime("2026-06-01T12:00:00Z")).toMatch(/Jun 1/)
  })
})
