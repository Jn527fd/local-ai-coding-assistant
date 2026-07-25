import { useEffect, useRef, type ReactNode } from "react"

export function CenteredModal({
  children,
  onRequestClose,
  ariaLabel,
  ariaLabelledBy,
  initialFocusRef,
  returnFocusRef,
  maxWidth = 520,
}: {
  children: ReactNode
  onRequestClose: () => void
  ariaLabel?: string
  ariaLabelledBy?: string
  initialFocusRef?: { current: HTMLElement | null }
  returnFocusRef?: { current: HTMLElement | null }
  maxWidth?: number
}) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const previousFocusRef = useRef<HTMLElement | null>(null)
  const closeRequestRef = useRef(onRequestClose)

  useEffect(() => {
    closeRequestRef.current = onRequestClose
  }, [onRequestClose])

  useEffect(() => {
    previousFocusRef.current = (document.activeElement as HTMLElement | null)
    const returnTarget = returnFocusRef?.current ?? previousFocusRef.current
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = "hidden"

    const focusFrame = window.requestAnimationFrame(() => {
      ;(initialFocusRef?.current ?? dialogRef.current)?.focus()
    })

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault()
        closeRequestRef.current()
        return
      }

      if (event.key !== "Tab") return

      const focusableElements = Array.from(
        dialogRef.current?.querySelectorAll<HTMLElement>(
          'button:not(:disabled), input:not(:disabled), textarea:not(:disabled), select:not(:disabled), [tabindex]:not([tabindex="-1"])',
        ) ?? [],
      ).filter((element) => !element.hasAttribute("hidden"))

      if (focusableElements.length === 0) {
        event.preventDefault()
        dialogRef.current?.focus()
        return
      }

      const firstElement = focusableElements[0]
      const lastElement = focusableElements[focusableElements.length - 1]

      if (event.shiftKey && document.activeElement === firstElement) {
        event.preventDefault()
        lastElement.focus()
      } else if (!event.shiftKey && document.activeElement === lastElement) {
        event.preventDefault()
        firstElement.focus()
      }
    }

    document.addEventListener("keydown", handleKeyDown)

    return () => {
      window.cancelAnimationFrame(focusFrame)
      document.removeEventListener("keydown", handleKeyDown)
      document.body.style.overflow = previousOverflow
      if (returnTarget?.isConnected) returnTarget.focus()
    }
  }, [initialFocusRef, returnFocusRef])

  return (
    <div
      className="centered-modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) closeRequestRef.current()
      }}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 60,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 20,
        background: "color-mix(in srgb, var(--app-bg) 38%, rgba(5,10,20,0.56))",
        backdropFilter: "blur(4px)",
        animation: "modalBackdropIn 160ms ease-out",
      }}
    >
      <div
        ref={dialogRef}
        className="centered-modal-container"
        role="dialog"
        aria-modal="true"
        aria-label={ariaLabel}
        aria-labelledby={ariaLabelledBy}
        tabIndex={-1}
        style={{
          width: `min(${maxWidth}px, 100%)`,
          maxHeight: "calc(100dvh - 40px)",
          display: "flex",
          flexDirection: "column",
          background: "var(--app-surface)",
          backdropFilter: "blur(20px)",
          borderRadius: 16,
          border:
            "1px solid color-mix(in srgb, var(--app-border) 72%, transparent)",
          boxShadow: "var(--app-shadow)",
          overflow: "hidden",
          animation: "modalContentIn 180ms cubic-bezier(0.2,0.8,0.2,1)",
        }}
      >
        {children}
      </div>
    </div>
  )
}
