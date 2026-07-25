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
    ocrEngine: firstAvailableId(capabilities.ocrEngines) ?? fallback.ocrEngine,
    pdfParser: firstAvailableId(capabilities.pdfParsers) ?? fallback.pdfParser,
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
