import { createRef } from "react"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import type {
  ComponentCapabilities,
  ModelConfiguration,
} from "../../domain/models"
import { ChatConfigurationModal } from "./ChatConfigurationModal"

const configuration: ModelConfiguration = {
  llmModel: "qwen3:4b",
  visionModel: "llava:7b",
  embedder: "all-minilm",
  ocrEngine: "none",
  pdfParser: "pymupdf",
  vectorDatabase: "chroma",
  contextCompressor: "token",
  reranker: "none",
}

const capabilities: ComponentCapabilities = {
  llmModels: [
    {
      id: "qwen3:4b",
      label: "qwen3:4b",
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
  rerankerModels: [
    {
      id: "none",
      label: "None",
      type: "rerankerModel",
      available: true,
      source: "builtin",
    },
  ],
  visionModels: [
    {
      id: "llava:7b",
      label: "llava:7b",
      type: "visionModel",
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
    {
      id: "tesseract",
      label: "Tesseract",
      type: "ocrEngine",
      available: false,
      source: "local",
    },
  ],
  pdfParsers: [
    {
      id: "pymupdf",
      label: "PyMuPDF",
      type: "pdfParser",
      available: true,
      source: "local",
    },
  ],
  chunkers: [],
  vectorDatabases: [
    {
      id: "chroma",
      label: "Chroma",
      type: "vectorDatabase",
      available: true,
      source: "static",
    },
  ],
  ragPipelines: [],
  contextCompressors: [
    {
      id: "token",
      label: "Token",
      type: "contextCompressor",
      available: true,
      source: "static",
    },
  ],
  unknownOllamaModels: [],
}

describe("ChatConfigurationModal", () => {
  it("renders backend capability options and reports changes", async () => {
    const user = userEvent.setup()
    const onConfigurationChange = vi.fn()
    renderModal({ onConfigurationChange })

    expect(screen.getByRole("combobox", { name: "LLM Model" })).toHaveValue(
      "qwen3:4b",
    )
    expect(
      screen.queryByRole("combobox", { name: "OCR Engine" }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole("combobox", { name: "PDF Parser" }),
    ).not.toBeInTheDocument()

    await user.selectOptions(
      screen.getByRole("combobox", { name: "Context Compressor" }),
      "token",
    )

    expect(onConfigurationChange).toHaveBeenCalledWith(
      "contextCompressor",
      "token",
    )
  })

  it("shows empty and error states without crashing", () => {
    renderModal({
      capabilities: null,
      capabilitiesError: "Ollama is offline",
      capabilitiesLoading: true,
    })

    expect(
      screen.getByText("Loading local capabilities..."),
    ).toBeInTheDocument()
    expect(screen.getByText(/Capability discovery failed/)).toBeInTheDocument()
    expect(
      screen.getByRole("combobox", { name: "LLM Model" }),
    ).toBeInTheDocument()
  })
})

function renderModal({
  onConfigurationChange = vi.fn(),
  capabilities: capabilityCatalog = capabilities,
  capabilitiesLoading = false,
  capabilitiesError = "",
}: {
  onConfigurationChange?: (
    field: keyof ModelConfiguration,
    value: ModelConfiguration[keyof ModelConfiguration],
  ) => void
  capabilities?: ComponentCapabilities | null
  capabilitiesLoading?: boolean
  capabilitiesError?: string
} = {}) {
  return render(
    <ChatConfigurationModal
      open={true}
      onClose={() => undefined}
      llmModelSelectRef={createRef<HTMLSelectElement>()}
      returnFocusRef={createRef<HTMLButtonElement>()}
      configuration={configuration}
      capabilities={capabilityCatalog}
      capabilitiesLoading={capabilitiesLoading}
      capabilitiesError={capabilitiesError}
      onConfigurationChange={onConfigurationChange}
      saveStatus="idle"
      saveError=""
    />,
  )
}
