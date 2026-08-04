export const SETTINGS_STORAGE_KEY = "localchat.settings.v1"
export const SETTINGS_CHANGED_EVENT = "localchat:settings-changed"

export type ThemeMode = "light" | "dark"
export type TextSizeMode = "small" | "default" | "large"

export interface AppSettings {
  theme: ThemeMode
  textSize: TextSizeMode
  sendOnEnter: boolean
  showMessageTimestamps: boolean
  confirmBeforeDeleteChats: boolean
}

export const DEFAULT_APP_SETTINGS: AppSettings = {
  theme: "light",
  textSize: "default",
  sendOnEnter: true,
  showMessageTimestamps: true,
  confirmBeforeDeleteChats: true,
}

export function loadAppSettings(): AppSettings {
  try {
    const raw = window.localStorage.getItem(SETTINGS_STORAGE_KEY)
    if (!raw) return { ...DEFAULT_APP_SETTINGS }

    const parsed = JSON.parse(raw) as Partial<AppSettings>
    return {
      theme:
        parsed.theme === "light" || parsed.theme === "dark"
          ? parsed.theme
          : DEFAULT_APP_SETTINGS.theme,
      textSize:
        parsed.textSize === "small" ||
        parsed.textSize === "default" ||
        parsed.textSize === "large"
          ? parsed.textSize
          : DEFAULT_APP_SETTINGS.textSize,
      sendOnEnter:
        typeof parsed.sendOnEnter === "boolean"
          ? parsed.sendOnEnter
          : DEFAULT_APP_SETTINGS.sendOnEnter,
      showMessageTimestamps:
        typeof parsed.showMessageTimestamps === "boolean"
          ? parsed.showMessageTimestamps
          : DEFAULT_APP_SETTINGS.showMessageTimestamps,
      confirmBeforeDeleteChats:
        typeof parsed.confirmBeforeDeleteChats === "boolean"
          ? parsed.confirmBeforeDeleteChats
          : DEFAULT_APP_SETTINGS.confirmBeforeDeleteChats,
    }
  } catch {
    return { ...DEFAULT_APP_SETTINGS }
  }
}

export function persistAppSettings(settings: AppSettings) {
  window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings))
}

export function applyAppSettings(settings: AppSettings) {
  const root = document.documentElement
  root.dataset.theme = settings.theme
  root.dataset.textSize = settings.textSize
  root.style.fontSize =
    settings.textSize === "small"
      ? "15px"
      : settings.textSize === "large"
        ? "18px"
        : "16px"
}

export function announceSettingsChanged() {
  window.dispatchEvent(new CustomEvent(SETTINGS_CHANGED_EVENT))
}
