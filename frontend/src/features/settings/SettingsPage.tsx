import { useEffect, useMemo, useRef, useState } from "react"
import { Link } from "react-router-dom"
import { ConfirmationModal } from "../../components/ConfirmationModal"
import {
  announceSettingsChanged,
  applyAppSettings,
  DEFAULT_APP_SETTINGS,
  loadAppSettings,
  persistAppSettings,
  type AppSettings,
  type TextSizeMode,
  type ThemeMode,
} from "./settingsStorage"

export function SettingsPage() {
  const [initialSettings] = useState(loadAppSettings)
  const [savedSettings, setSavedSettings] =
    useState<AppSettings>(initialSettings)
  const [draft, setDraft] = useState<AppSettings>(initialSettings)
  const [notice, setNotice] = useState("")

  const [resetOpen, setResetOpen] = useState(false)

  const resetCancelRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    applyAppSettings(initialSettings)
  }, [initialSettings])

  const dirty = useMemo(
    () => JSON.stringify(draft) !== JSON.stringify(savedSettings),

    [draft, savedSettings],
  )

  const updateDraft = <Key extends keyof AppSettings,>(
    key: Key,
    value: AppSettings[Key],
  ) => {
    setDraft((current) => ({ ...current, [key]: value }))

    setNotice("")
  }

  const saveSettings = () => {
    persistAppSettings(draft)
    setSavedSettings(draft)
    applyAppSettings(draft)
    announceSettingsChanged()
    setNotice("Settings saved.")
  }

  const cancelSettings = () => {
    setDraft(savedSettings)

    applyAppSettings(savedSettings)
    announceSettingsChanged()
    setNotice("Changes canceled.")
  }

  const openResetConfirmation = () => {
    setResetOpen(true)
  }

  const confirmResetSettings = () => {
    const resetToDefaults = { ...DEFAULT_APP_SETTINGS }
    persistAppSettings(resetToDefaults)
    setSavedSettings(resetToDefaults)

    setDraft(resetToDefaults)

    applyAppSettings(resetToDefaults)
    announceSettingsChanged()
    setResetOpen(false)

    setNotice("Settings reset to defaults.")
  }

  return (
    <div className="profile-page-shell">
      <a className="skip-link" href="#settings-main">
        Skip to settings content
      </a>

      <header className="profile-topbar">
        <Link to="/chat" className="profile-brand" aria-label="LocalChat home">
          <span aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path
                d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z"
                fill="currentColor"
              />
            </svg>
          </span>
          LocalChat
        </Link>
        <Link to="/chat" className="profile-back-link">
          <svg
            width="17"
            height="17"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="m15 18-6-6 6-6"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          Back to chat
        </Link>
      </header>

      <main id="settings-main" className="profile-main" tabIndex={-1}>
        <div className="profile-page-heading">
          <span className="profile-page-kicker">Application settings</span>
          <h1>Settings</h1>
          <p>Customize the LocalChat experience for this device.</p>
        </div>

        <section className="profile-card">
          <div className="profile-section-heading">
            <div>
              <h2>Appearance</h2>
              <p>Choose how the app looks and how easy it is to read.</p>
            </div>
          </div>

          <div className="profile-fields-grid">
            <div className="profile-field">
              <label htmlFor="theme-setting">Theme</label>
              <select
                id="theme-setting"
                value={draft.theme}
                onChange={(event) =>
                  updateDraft("theme", event.target.value as ThemeMode)
                }
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
              </select>
            </div>

            <div className="profile-field">
              <label htmlFor="text-size-setting">Text size</label>
              <select
                id="text-size-setting"
                value={draft.textSize}
                onChange={(event) =>
                  updateDraft("textSize", event.target.value as TextSizeMode)
                }
              >
                <option value="small">Small</option>
                <option value="default">Default</option>
                <option value="large">Large</option>
              </select>
            </div>
          </div>
        </section>

        <section className="profile-card">
          <div className="profile-section-heading">
            <div>
              <h2>Chat</h2>
              <p>
                Choose the behavior you want while composing and managing chats.
              </p>
            </div>
          </div>

          <div className="profile-fields-grid">
            <label className="settings-toggle-field" htmlFor="send-on-enter">
              <input
                id="send-on-enter"
                type="checkbox"
                checked={draft.sendOnEnter}
                onChange={(event) =>
                  updateDraft("sendOnEnter", event.target.checked)
                }
              />
              <span>
                <strong>Send messages with Enter</strong>
                <small>
                  Press Enter to send and Shift+Enter for a newline.
                </small>
              </span>
            </label>

            <label className="settings-toggle-field" htmlFor="show-timestamps">
              <input
                id="show-timestamps"
                type="checkbox"
                checked={draft.showMessageTimestamps}
                onChange={(event) =>
                  updateDraft("showMessageTimestamps", event.target.checked)
                }
              />
              <span>
                <strong>Show message timestamps</strong>
                <small>Display times beside messages in the transcript.</small>
              </span>
            </label>

            <label
              className="settings-toggle-field settings-toggle-field-wide"
              htmlFor="confirm-delete-chats"
            >
              <input
                id="confirm-delete-chats"
                type="checkbox"
                checked={draft.confirmBeforeDeleteChats}
                onChange={(event) =>
                  updateDraft("confirmBeforeDeleteChats", event.target.checked)
                }
              />
              <span>
                <strong>Confirm before deleting chats</strong>
                <small>
                  Require confirmation before removing a conversation.
                </small>
              </span>
            </label>
          </div>
        </section>

        <section className="profile-card profile-actions-card">
          <div>
            <h2>Actions</h2>
            <p>Save your choices or restore the defaults for this device.</p>
          </div>
          <div className="profile-data-actions">
            <button
              type="button"
              className="profile-secondary-button"
              onClick={openResetConfirmation}
            >
              Reset to defaults
            </button>
          </div>
        </section>
      </main>

      {notice && (
        <div className="profile-toast" role="status">
          <span aria-hidden="true">✓</span>
          {notice}
          <button
            type="button"
            onClick={() => setNotice("")}
            aria-label="Dismiss notification"
          >
            ×
          </button>
        </div>
      )}

      <div className="profile-sticky-actions">
        <p aria-live="polite">
          {dirty ? "You have unsaved changes." : "All changes are saved."}
        </p>
        <div>
          <button
            type="button"
            className="profile-secondary-button"
            onClick={cancelSettings}
            disabled={!dirty}
          >
            Cancel
          </button>
          <button
            type="button"
            className="profile-primary-button"
            onClick={saveSettings}
            disabled={!dirty}
          >
            Save changes
          </button>
        </div>
      </div>

      <ConfirmationModal
        request={
          resetOpen
            ? {
                title: "Reset settings to defaults?",

                description:
                  "This will restore your LocalChat appearance and chat preferences to the default device values.",

                confirmLabel: "Reset settings",

                tone: "danger",

                onConfirm: confirmResetSettings,
              }
            : null
        }
        pending={false}
        error=""
        cancelButtonRef={resetCancelRef}
        onCancel={() => setResetOpen(false)}
        onConfirm={confirmResetSettings}
      />
    </div>
  )
}
