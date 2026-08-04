import type {
  ComponentCapabilities,
  ComponentCapability,
  ModelConfiguration,
} from "../domain/models"

export const emptyComponentCapabilities = (): ComponentCapabilities => ({
  llmModels: [],
  embedderModels: [],
  rerankerModels: [],
  visionModels: [],
  ocrEngines: [],
  pdfParsers: [],
  chunkers: [],
  vectorDatabases: [],
  ragPipelines: [],
  contextCompressors: [],
  unknownOllamaModels: [],
})

export function normalizeComponentCapabilities(
  response: Partial<ComponentCapabilities> | null | undefined,
): ComponentCapabilities {
  const empty = emptyComponentCapabilities()
  return Object.fromEntries(
    Object.entries(empty).map(([key]) => [
      key,
      normalizeCapabilityList(response?.[(key as keyof ComponentCapabilities)]),
    ]),
  ) as unknown as ComponentCapabilities
}

export function createConfigurationFromCapabilities(
  capabilities: ComponentCapabilities | null | undefined,
  fallback: ModelConfiguration,
): ModelConfiguration {
  if (!capabilities) return { ...fallback }
  return {
    ...fallback,
    llmModel: firstAvailableId(capabilities.llmModels) ?? fallback.llmModel,
    visionModel:
      firstAvailableId(capabilities.visionModels) ?? fallback.visionModel,
    embedder:
      firstAvailableId(capabilities.embedderModels) ?? fallback.embedder,
    ocrEngine:
      preferredAvailableId(capabilities.ocrEngines, ["paddleocr"]) ??
      fallback.ocrEngine,
    pdfParser:
      preferredAvailableId(capabilities.pdfParsers, ["docling"]) ??
      fallback.pdfParser,
    vectorDatabase:
      firstAvailableId(capabilities.vectorDatabases) ?? fallback.vectorDatabase,
    contextCompressor:
      firstAvailableId(capabilities.contextCompressors) ??
      fallback.contextCompressor,
    reranker:
      firstAvailableId(capabilities.rerankerModels) ?? fallback.reranker,
  }
}

function normalizeCapabilityList(
  capabilities: ComponentCapability[] | undefined,
): ComponentCapability[] {
  return [...(capabilities ?? [])]
    .filter((capability) => capability && typeof capability.id === "string")
    .map((capability) => ({
      ...capability,
      label: capability.label || capability.name || capability.id,
      available: Boolean(capability.available),
      source: capability.source || "unknown",
      type: capability.type || "capability",
    }))
    .sort((a, b) => a.label.localeCompare(b.label))
}

function firstAvailableId(capabilities: ComponentCapability[]) {
  return capabilities.find((capability) => capability.available)?.id
}

function preferredAvailableId(
  capabilities: ComponentCapability[],
  preferredIds: string[],
) {
  for (const preferredId of preferredIds) {
    const match = capabilities.find(
      (capability) => capability.available && capability.id === preferredId,
    )
    if (match) return match.id
  }
  return firstAvailableId(capabilities)
}
