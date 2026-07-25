import type { CSSProperties, RefObject } from "react"
import { CenteredModal } from "../../components/CenteredModal"
import type {
  ComponentCapabilities,
  ComponentCapability,
  ModelConfiguration,
} from "../../domain/models"

interface CapabilitySelectDefinition<Key extends keyof ModelConfiguration> {
  field: Key
  label: string
  capabilities: ComponentCapability[]
  required?: boolean
}

export function ChatConfigurationModal({
  open,
  onClose,
  llmModelSelectRef,
  returnFocusRef,
  configuration,
  capabilities,
  capabilitiesLoading,
  capabilitiesError,
  onConfigurationChange,
  saveStatus,
  saveError,
}: {
  open: boolean
  onClose: () => void
  llmModelSelectRef: RefObject<HTMLSelectElement | null>
  returnFocusRef: RefObject<HTMLButtonElement | null>
  configuration: ModelConfiguration
  capabilities: ComponentCapabilities | null
  capabilitiesLoading?: boolean
  capabilitiesError?: string
  onConfigurationChange: <Key extends keyof ModelConfiguration,>(
    field: Key,
    value: ModelConfiguration[Key],
  ) => void
  saveStatus: "idle" | "saving" | "saved" | "error"
  saveError: string
}) {
  if (!open) return null

  const selections: CapabilitySelectDefinition<keyof ModelConfiguration>[] = [
    {
      field: "llmModel",
      label: "LLM Model",
      capabilities: capabilities?.llmModels ?? [],
      required: true,
    },
    {
      field: "visionModel",
      label: "Vision Model",
      capabilities: capabilities?.visionModels ?? [],
      required: true,
    },
    {
      field: "embedder",
      label: "Embedding Model",
      capabilities: capabilities?.embedderModels ?? [],
    },
    {
      field: "ocrEngine",
      label: "OCR Engine",
      capabilities: capabilities?.ocrEngines ?? [],
    },
    {
      field: "pdfParser",
      label: "PDF Parser",
      capabilities: capabilities?.pdfParsers ?? [],
    },
    {
      field: "vectorDatabase",
      label: "Vector Database",
      capabilities: capabilities?.vectorDatabases ?? [],
    },
    {
      field: "contextCompressor",
      label: "Context Compressor",
      capabilities: capabilities?.contextCompressors ?? [],
    },
    {
      field: "reranker",
      label: "ReRanker",
      capabilities: capabilities?.rerankerModels ?? [],
    },
  ]

  return (
    <CenteredModal
      ariaLabelledBy="chat-configuration-title"
      initialFocusRef={llmModelSelectRef}
      returnFocusRef={returnFocusRef}
      onRequestClose={onClose}
      maxWidth={620}
    >
      <div className="chat-config-header">
        <div>
          <h2 id="chat-configuration-title">Chat Configuration</h2>
          <p>Choose the models and tools used for this conversation.</p>
        </div>
        <button
          type="button"
          aria-label="Close chat configuration"
          onClick={onClose}
          className="icon-close-button"
        >
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
            <path
              d="M18 6 6 18M6 6l12 12"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
        </button>
      </div>
      <div className="chat-config-content">
        <div
          className={
            saveStatus === "error" || capabilitiesError
              ? "configuration-save-state is-error"
              : "sr-only"
          }
          aria-live="polite"
        >
          {saveStatus === "saving" && "Saving conversation configuration..."}
          {saveStatus === "saved" && "Configuration saved"}
          {saveStatus === "error" &&
            (saveError || "Configuration could not be saved")}
          {capabilitiesError &&
            `Capability discovery failed: ${capabilitiesError}`}
        </div>
        {capabilitiesLoading && (
          <p className="context-modelfile-help" aria-live="polite">
            Loading local capabilities...
          </p>
        )}
        {selections.map((selection) => (
          <CapabilitySelect
            key={selection.field}
            definition={selection}
            configuration={configuration}
            selectRef={
              selection.field === "llmModel" ? llmModelSelectRef : undefined
            }
            onConfigurationChange={onConfigurationChange}
          />
        ))}
      </div>
    </CenteredModal>
  )
}

function CapabilitySelect<Key extends keyof ModelConfiguration>({
  definition,
  configuration,
  selectRef,
  onConfigurationChange,
}: {
  definition: CapabilitySelectDefinition<Key>
  configuration: ModelConfiguration
  selectRef?: RefObject<HTMLSelectElement | null>
  onConfigurationChange: <Field extends keyof ModelConfiguration,>(
    field: Field,
    value: ModelConfiguration[Field],
  ) => void
}) {
  const currentValue = configuration[definition.field] ?? ""
  const options = withCurrentValue(definition.capabilities, currentValue)
  const availableOptions = options.filter((capability) => capability.available)
  const disabled = definition.required && availableOptions.length === 0

  return (
    <label style={labelStyle}>
      {definition.label}
      <select
        ref={selectRef}
        value={String(currentValue)}
        disabled={disabled}
        onChange={(event) =>
          onConfigurationChange(
            definition.field,
            event.target.value as ModelConfiguration[Key],
          )
        }
        style={selectStyle}
      >
        {options.length === 0 && (
          <option value="">
            {definition.required
              ? "No available capability detected"
              : "No selection"}
          </option>
        )}
        {options.map((capability) => (
          <option
            key={capability.id}
            value={capability.id}
            disabled={!capability.available}
          >
            {capability.label}
            {!capability.available ? " (unavailable)" : ""}
          </option>
        ))}
      </select>
    </label>
  )
}

function withCurrentValue(
  capabilities: ComponentCapability[],
  currentValue: unknown,
): ComponentCapability[] {
  const currentId = typeof currentValue === "string" ? currentValue : ""
  if (
    !currentId ||
    capabilities.some((capability) => capability.id === currentId)
  ) {
    return capabilities
  }
  return [
    {
      id: currentId,
      label: currentId,
      type: "current",
      available: true,
      source: "conversation",
    },
    ...capabilities,
  ]
}

const labelStyle = {
  display: "flex",
  flexDirection: "column",
  gap: 6,
  marginBottom: 14,
  color: "#1a2340",
  fontSize: 12,
  fontWeight: 700,
} satisfies CSSProperties

const selectStyle = {
  width: "100%",
  padding: "9px 10px",
  borderRadius: 8,
  border: "1px solid rgba(200,220,255,0.7)",
  background: "rgba(248,251,255,0.95)",
  cursor: "pointer",
  fontSize: 13,
  color: "#1a2340",
  fontWeight: 400,
  fontFamily: "inherit",
  outline: "none",
} satisfies CSSProperties
