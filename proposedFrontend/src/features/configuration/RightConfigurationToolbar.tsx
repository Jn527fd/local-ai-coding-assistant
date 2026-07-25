import type { Dispatch, RefObject, SetStateAction } from "react"
import { RightBtn } from "../../components/ToolbarButtons"

export function RightConfigurationToolbar({
  tempChat,
  onTemporaryChange,
  activeRight,
  setActiveRight,
  chatConfigButtonRef,
  contextButtonRef,
  contextOpen,
  savedSystemPrompt,
  openContextModal,
  sourcesButtonRef,
  sourcesOpen,
  selectedSources,
  setSourcesOpen,
}: {
  tempChat: boolean
  onTemporaryChange: (temporary: boolean) => void
  activeRight: string | null
  setActiveRight: Dispatch<SetStateAction<string | null>>
  chatConfigButtonRef: RefObject<HTMLButtonElement | null>
  contextButtonRef: RefObject<HTMLButtonElement | null>
  contextOpen: boolean
  savedSystemPrompt: string
  openContextModal: () => void
  sourcesButtonRef: RefObject<HTMLButtonElement | null>
  sourcesOpen: boolean
  selectedSources: Set<string>
  setSourcesOpen: Dispatch<SetStateAction<boolean>>
}) {
  return (
    <aside
      className="right-configuration-toolbar"
      aria-label="Conversation tools"
      style={{
        position: "fixed",
        top: 0,
        right: 0,
        height: "100vh",
        width: 52,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        paddingTop: 14,
        gap: 4,
        zIndex: 40,
        background: "var(--app-surface)",
        backdropFilter: "blur(14px)",
        borderLeft:
          "1px solid color-mix(in srgb, var(--app-border) 72%, transparent)",
      }}
    >
      {/* Temp chat toggle */}
      <RightBtn
        active={tempChat}
        label="Temp Chat"
        onClick={() => onTemporaryChange(!tempChat)}
        title="Temporary chat (not saved)"
        ariaPressed={tempChat}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 2a10 10 0 1 1 0 20A10 10 0 0 1 12 2z"
            stroke="currentColor"
            strokeWidth="1.8"
          />
          <path
            d="M12 6v6l4 2"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      </RightBtn>

      <div
        style={{
          width: 24,
          height: 1,
          background: "color-mix(in srgb, var(--app-border) 72%, transparent)",
          margin: "2px 0",
        }}
      />

      {/* Chat Configuration */}
      <RightBtn
        buttonRef={chatConfigButtonRef}
        active={activeRight === "model"}
        label="M"
        onClick={() => setActiveRight((v) => (v === "model" ? null : "model"))}
        title="Chat Configuration"
        badge="M"
        ariaHasPopup="dialog"
        ariaExpanded={activeRight === "model"}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path
            d="M4 6h7M15 6h5M4 12h2M10 12h10M4 18h9M17 18h3"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
          <circle
            cx="13"
            cy="6"
            r="2"
            stroke="currentColor"
            strokeWidth="1.8"
          />
          <circle
            cx="8"
            cy="12"
            r="2"
            stroke="currentColor"
            strokeWidth="1.8"
          />
          <circle
            cx="15"
            cy="18"
            r="2"
            stroke="currentColor"
            strokeWidth="1.8"
          />
        </svg>
      </RightBtn>

      {/* Context prompt */}
      <RightBtn
        buttonRef={contextButtonRef}
        active={contextOpen || savedSystemPrompt.trim().length > 0}
        label="C"
        onClick={openContextModal}
        title="Context / system prompt"
        ariaHasPopup="dialog"
        ariaExpanded={contextOpen}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path
            d="M4 6h16M4 10h10M4 14h12M4 18h8"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      </RightBtn>

      {/* Sources */}
      <RightBtn
        buttonRef={sourcesButtonRef}
        active={sourcesOpen || selectedSources.size > 0}
        label="Sources"
        onClick={() => {
          setActiveRight(null)
          setSourcesOpen(true)
        }}
        title="Sources"
        ariaHasPopup="dialog"
        ariaExpanded={sourcesOpen}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path
            d="M4 19V5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v14"
            stroke="currentColor"
            strokeWidth="1.8"
          />
          <path
            d="M4 19h16M9 3v10l3-2 3 2V3"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </RightBtn>
    </aside>
  )
}
