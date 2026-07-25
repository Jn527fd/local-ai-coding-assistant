import { describe, expect, it } from "vitest"
import { createDefaultModelConfiguration } from "../domain/defaults"
import {
  createConfigurationFromCapabilities,
  normalizeComponentCapabilities,
} from "./capabilities"

describe("component capability helpers", () => {
  it("normalizes missing categories and sorts labels", () => {
    const capabilities = normalizeComponentCapabilities({
      llmModels: [
        {
          id: "zeta",
          label: "Zeta",
          type: "llmModel",
          available: true,
          source: "ollama",
        },
        {
          id: "alpha",
          label: "",
          type: "llmModel",
          available: true,
          source: "ollama",
          name: "Alpha",
        },
      ],
    })

    expect(capabilities.llmModels.map((item) => item.label)).toEqual([
      "Alpha",
      "Zeta",
    ])
    expect(capabilities.embedderModels).toEqual([])
    expect(capabilities.contextCompressors).toEqual([])
  })

  it("builds defaults from the first available backend capabilities", () => {
    const fallback = createDefaultModelConfiguration()
    const capabilities = normalizeComponentCapabilities({
      llmModels: [
        {
          id: "offline-llm",
          label: "offline-llm",
          type: "llmModel",
          available: false,
          source: "ollama",
        },
        {
          id: "alpha-llm",
          label: "alpha-llm",
          type: "llmModel",
          available: true,
          source: "ollama",
        },
      ],
      embedderModels: [
        {
          id: "all-minilm",
          label: "all-minilm",
          type: "embedderModel",
          available: true,
          source: "ollama",
        },
      ],
      ocrEngines: [
        {
          id: "none",
          label: "None",
          type: "ocrEngine",
          available: true,
          source: "builtin",
        },
      ],
    })

    expect(
      createConfigurationFromCapabilities(capabilities, fallback),
    ).toMatchObject({
      llmModel: "alpha-llm",
      embedder: "all-minilm",
      ocrEngine: "none",
      visionModel: fallback.visionModel,
    })
  })
})
