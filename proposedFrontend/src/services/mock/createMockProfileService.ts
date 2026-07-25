import type { ProfileService } from "../contracts"
import { mockUserProfile } from "./mockProfileData"

const MOCK_PROFILE_KEY = "localchat.mock-profile.v1"

export type ProfileMockOperation = "profile.load" | "profile.update" | "profile.uploadAvatar" | "profile.export"

interface MockProfileServiceBundle {
  service: ProfileService
  reset: () => void
}

export function createMockProfileService(
  simulate: (operation: ProfileMockOperation) => Promise<void>,
): MockProfileServiceBundle {
  let profile = readStoredProfile() ?? clone(mockUserProfile)

  const service: ProfileService = {
    capabilities: {
      avatarUpload: true,
      persistence: "local",
    },
    // TODO(backend): Replace with GET /api/profile in the HTTP profile adapter.
    async load() {
      await simulate("profile.load")
      return { profile: clone(profile) }
    },

    // TODO(backend): Replace with PATCH /api/profile.
    async update(input) {
      await simulate("profile.update")
      profile = {
        ...profile,
        ...input,
        displayName: input.displayName.trim(),
        handle: input.handle.trim(),
        preferredName: input.preferredName.trim(),
        role: input.role.trim(),
        about: input.about.trim(),
      }
      writeStoredProfile(profile)
      return { profile: clone(profile), updatedAt: new Date().toISOString() }
    },

    // TODO(backend): Replace with POST /api/profile/avatar and return its URL.
    async uploadAvatar(file) {
      await simulate("profile.uploadAvatar")
      const avatarUrl = await readFileAsDataUrl(file)
      profile = { ...profile, avatarUrl }
      writeStoredProfile(profile)
      return { avatarUrl }
    },

    // TODO(backend): Replace with GET /api/profile/export.
    async exportData() {
      await simulate("profile.export")
      return {
        filename: "localchat-profile.json",
        mediaType: "application/json",
        content: JSON.stringify(profile, null, 2),
      }
    },
  }

  return {
    service,
    reset() {
      profile = clone(mockUserProfile)
      clearStoredProfile()
    },
  }
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.addEventListener("load", () => resolve(String(reader.result)))
    reader.addEventListener("error", () =>
      reject(reader.error ?? new Error("The avatar could not be read.")),
    )
    reader.readAsDataURL(file)
  })
}

function clone<Value>(value: Value): Value {
  return structuredClone(value)
}

function readStoredProfile() {
  try {
    const serialized = globalThis.localStorage?.getItem(MOCK_PROFILE_KEY)
    if (!serialized) return null
    const profile: unknown = JSON.parse(serialized)
    return isStoredProfile(profile) ? clone(profile) : null
  } catch {
    return null
  }
}

function writeStoredProfile(profile: typeof mockUserProfile) {
  try {
    globalThis.localStorage?.setItem(MOCK_PROFILE_KEY, JSON.stringify(profile))
  } catch {
    // The mock remains usable when browser storage is restricted or full.
  }
}

function clearStoredProfile() {
  try {
    globalThis.localStorage?.removeItem(MOCK_PROFILE_KEY)
  } catch {
    // Browser storage may be unavailable in tests or restricted contexts.
  }
}

function isStoredProfile(value: unknown): value is typeof mockUserProfile {
  if (!value || typeof value !== "object") return false
  const candidate = value as Partial<typeof mockUserProfile>
  return (
    typeof candidate.id === "string" &&
    typeof candidate.displayName === "string" &&
    typeof candidate.handle === "string" &&
    typeof candidate.preferredName === "string" &&
    (candidate.avatarUrl === null || typeof candidate.avatarUrl === "string") &&
    typeof candidate.role === "string" &&
    typeof candidate.about === "string" &&
    typeof candidate.preferredLanguage === "string" &&
    ["concise", "balanced", "detailed"].includes(
      String(candidate.responsePreference),
    ) &&
    ["member", "admin"].includes(String(candidate.accountType)) &&
    typeof candidate.deviceName === "string" &&
    typeof candidate.joinedAt === "string" &&
    typeof candidate.storageLocation === "string"
  )
}
