import { useState, type ReactNode, type RefObject } from "react"

export function RightBtn({
  children,
  active,
  onClick,
  title,
  buttonRef,
  ariaHasPopup,
  ariaExpanded,
  ariaControls,
  ariaPressed,
}: {
  children: ReactNode
  active: boolean
  label?: string
  badge?: string
  onClick: () => void
  title: string
  buttonRef?: RefObject<HTMLButtonElement | null>
  ariaHasPopup?: "menu" | "dialog"
  ariaExpanded?: boolean
  ariaControls?: string
  ariaPressed?: boolean
}) {
  return (
    <button
      ref={buttonRef}
      type="button"
      onClick={onClick}
      title={title}
      aria-label={title}
      aria-haspopup={ariaHasPopup}
      aria-expanded={ariaExpanded}
      aria-controls={ariaControls}
      aria-pressed={ariaPressed}
      style={{
        width: 36,
        height: 36,
        borderRadius: 10,
        border: active
          ? "1px solid rgba(79,142,247,0.4)"
          : "1px solid transparent",
        background: active ? "rgba(79,142,247,0.12)" : "transparent",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        cursor: "pointer",
        color: active ? "#3b6fd4" : "#506987",
        transition: "all 0.15s",
      }}
      onMouseEnter={(e) => {
        if (!active)
          e.currentTarget.style.background =
            "color-mix(in srgb, var(--app-accent) 10%, transparent)"
      }}
      onMouseLeave={(e) => {
        if (!active) e.currentTarget.style.background = "transparent"
      }}
    >
      {children}
    </button>
  )
}

export function SideIconBtn({
  children,
  title,
  active,
  onClick,
  buttonRef,
  ariaHasPopup,
  ariaExpanded,
  ariaControls,
}: {
  children: ReactNode
  title: string
  active?: boolean
  onClick: () => void
  buttonRef?: RefObject<HTMLButtonElement | null>
  ariaHasPopup?: "menu" | "dialog"
  ariaExpanded?: boolean
  ariaControls?: string
}) {
  return (
    <button
      ref={buttonRef}
      type="button"
      onClick={onClick}
      title={title}
      aria-label={title}
      aria-haspopup={ariaHasPopup}
      aria-expanded={ariaExpanded}
      aria-controls={ariaControls}
      style={{
        width: 36,
        height: 36,
        borderRadius: 10,
        border: active
          ? "1px solid rgba(79,142,247,0.4)"
          : "1px solid transparent",
        background: active ? "rgba(79,142,247,0.12)" : "transparent",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        cursor: "pointer",
        color: active ? "#3b6fd4" : "#506987",
        transition: "all 0.15s",
      }}
      onMouseEnter={(e) => {
        if (!active) {
          e.currentTarget.style.background =
            "color-mix(in srgb, var(--app-accent) 10%, transparent)"
          e.currentTarget.style.color = "var(--app-accent)"
        }
      }}
      onMouseLeave={(e) => {
        if (!active) {
          e.currentTarget.style.background = "transparent"
          e.currentTarget.style.color = "var(--app-muted-strong)"
        }
      }}
    >
      {children}
    </button>
  )
}

export function LogoButton({
  open,
  onToggle,
}: {
  open: boolean
  onToggle: () => void
}) {
  const [hovered, setHovered] = useState(false)

  return (
    <button
      type="button"
      onClick={onToggle}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      title={open ? "Close sidebar" : "Open sidebar"}
      aria-label={open ? "Close sidebar" : "Open sidebar"}
      aria-expanded={open}
      aria-controls="conversation-sidebar-content"
      style={{
        width: 32,
        height: 32,
        borderRadius: 10,
        background: hovered
          ? "linear-gradient(135deg,#3a7ef0 0%,#6a4e9a 100%)"
          : "linear-gradient(135deg,#4f8ef7 0%,#7b5ea7 100%)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        cursor: "pointer",
        border: "none",
        boxShadow: hovered ? "0 2px 12px rgba(79,142,247,0.4)" : "none",
        transition: "background 0.18s, box-shadow 0.18s",
      }}
    >
      {hovered ? (
        // Hamburger / arrow icon when hovered
        open ? (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path
              d="M15 18l-6-6 6-6"
              stroke="white"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        ) : (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path
              d="M4 6h16M4 12h16M4 18h16"
              stroke="white"
              strokeWidth="2.2"
              strokeLinecap="round"
            />
          </svg>
        )
      ) : (
        // Chat bubble logo at rest
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path
            d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"
            fill="white"
          />
        </svg>
      )}
    </button>
  )
}
