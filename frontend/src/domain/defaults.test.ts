import { describe, expect, it } from "vitest"
import {
  createDefaultConversationDraft,
  createDefaultModelConfiguration,
} from "./defaults"

describe("domain defaults", () => {
  it("maps a fresh conversation configuration without shared mutable state", () => {
    const first = createDefaultConversationDraft()
    const second = createDefaultConversationDraft()

    first.sourceIds.push("source-1")
    first.modelConfiguration.llmModel = "changed"

    expect(second).toEqual({
      systemPrompt: "",
      modelConfiguration: createDefaultModelConfiguration(),
      sourceIds: [],
      temporary: false,
    })
  })
})
