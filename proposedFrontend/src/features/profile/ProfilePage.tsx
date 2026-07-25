import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ChangeEvent,
  type FormEvent,
} from "react"
import { Link } from "react-router-dom"
import type { UpdateProfileRequestDto } from "../../domain/dtos"
import type { UserProfile } from "../../domain/models"
import { appServices, type ProfileService } from "../../services"
import {
  errorAsyncState,
  idleAsyncState,
  pendingAsyncState,
  successAsyncState,
  type AsyncState,
} from "../../services/asyncState"
import { normalizeError } from "../../services/errors"
import {
  ABOUT_LIMIT,
  ProfileForm,
  type ProfileValidationErrors,
} from "./ProfileForm"

const HANDLE_PATTERN = /^[A-Za-z0-9_.-]*$/

export function ProfilePage({
  profileService = appServices.profile,
}: {
  profileService?: ProfileService
}) {
  const [loadState, setLoadState] = useState<AsyncState<UserProfile>>(() =>
    pendingAsyncState(),
  )
  const [savedProfile, setSavedProfile] = useState<UserProfile | null>(null)
  const [draft, setDraft] = useState<UpdateProfileRequestDto | null>(null)
  const [avatarFile, setAvatarFile] = useState<File | null>(null)
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null)
  const [avatarError, setAvatarError] = useState("")
  const [saveState, setSaveState] = useState<AsyncState<UserProfile>>(() =>
    idleAsyncState(),
  )
  const [exporting, setExporting] = useState(false)
  const [notice, setNotice] = useState("")
  const avatarInputRef = useRef<HTMLInputElement>(null)
  const avatarUploadSupported =
    profileService.capabilities?.avatarUpload ?? true

  const applyLoadedProfile = (profile: UserProfile) => {
    setSavedProfile(profile)
    setDraft(toDraft(profile))
    setAvatarPreview(profile.avatarUrl)
    setLoadState(successAsyncState(profile))
  }

  const loadProfile = async () => {
    setLoadState(pendingAsyncState())
    try {
      const response = await profileService.load({ includeAvatar: true })
      applyLoadedProfile(response.profile)
    } catch (error) {
      setLoadState(errorAsyncState(normalizeError(error)))
    }
  }

  useEffect(() => {
    let active = true
    void profileService
      .load({ includeAvatar: true })
      .then((response) => {
        if (!active) return
        setSavedProfile(response.profile)
        setDraft(toDraft(response.profile))
        setAvatarPreview(response.profile.avatarUrl)
        setLoadState(successAsyncState(response.profile))
      })
      .catch((error) => {
        if (!active) return
        setLoadState(errorAsyncState(normalizeError(error)))
      })
    return () => {
      active = false
    }
  }, [profileService])

  useEffect(() => {
    return () => {
      if (avatarPreview?.startsWith("blob:")) URL.revokeObjectURL(avatarPreview)
    }
  }, [avatarPreview])

  const errors = useMemo(() => (draft ? validateProfile(draft) : {}), [draft])
  const dirty = Boolean(
    savedProfile &&
      draft &&
      (avatarFile ||
        JSON.stringify(draft) !== JSON.stringify(toDraft(savedProfile))),
  )

  const updateDraft = <Key extends keyof UpdateProfileRequestDto,>(
    key: Key,
    value: UpdateProfileRequestDto[Key],
  ) => {
    setDraft((current) => {
      if (!current) return current
      if (key === "displayName") {
        return {
          ...current,
          displayName: value as string,
          preferredName: value as string,
        }
      }
      return { ...current, [key]: value }
    })
    setSaveState(idleAsyncState())
    setNotice("")
  }

  const selectAvatar = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    if (
      !(["image/png", "image/jpeg", "image/webp"] as string[]).includes(
        file.type,
      )
    ) {
      setAvatarError("Choose a PNG, JPEG, or WebP image.")
      event.target.value = ""
      return
    }
    if (file.size > 2 * 1024 * 1024) {
      setAvatarError("Choose an image smaller than 2 MB.")
      event.target.value = ""
      return
    }
    setAvatarError("")
    setAvatarFile(file)
    setAvatarPreview(URL.createObjectURL(file))
    setSaveState(idleAsyncState())
    setNotice("")
  }

  const saveProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!draft || !savedProfile || !dirty || Object.keys(errors).length) return
    setSaveState(pendingAsyncState(savedProfile))
    setNotice("")
    try {
      let avatarUrl = savedProfile.avatarUrl
      if (avatarFile) {
        avatarUrl = (await profileService.uploadAvatar(avatarFile)).avatarUrl
      }
      const response = await profileService.update(draft)
      const updated = { ...response.profile, avatarUrl }
      setSavedProfile(updated)
      setDraft(toDraft(updated))
      setAvatarFile(null)
      setAvatarPreview(updated.avatarUrl)
      if (avatarInputRef.current) avatarInputRef.current.value = ""
      setSaveState(successAsyncState(updated))
      setNotice("Profile changes saved.")
    } catch (error) {
      setSaveState(errorAsyncState(normalizeError(error), savedProfile))
    }
  }

  const resetProfile = () => {
    if (!savedProfile) return
    setDraft(toDraft(savedProfile))
    setAvatarFile(null)
    setAvatarPreview(savedProfile.avatarUrl)
    setAvatarError("")
    setSaveState(idleAsyncState())
    setNotice("Changes reset.")
    if (avatarInputRef.current) avatarInputRef.current.value = ""
  }

  const exportProfile = async () => {
    setExporting(true)
    setNotice("")
    try {
      const result = await profileService.exportData()
      const url = URL.createObjectURL(
        new Blob([result.content], { type: result.mediaType }),
      )
      const link = document.createElement("a")
      link.href = url
      link.download = result.filename
      link.click()
      URL.revokeObjectURL(url)
      setNotice("Your profile export is ready.")
    } catch (error) {
      setNotice(normalizeError(error).message)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="profile-page-shell">
      <a className="skip-link" href="#profile-main">
        Skip to profile content
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

      <main id="profile-main" className="profile-main" tabIndex={-1}>
        <div className="profile-page-heading">
          <span className="profile-page-kicker">Local account</span>
          <h1>Profile</h1>
          <p>Manage how you appear and how the assistant addresses you.</p>
        </div>

        {loadState.status === "pending" && !savedProfile && (
          <ProfileLoadingState />
        )}
        {loadState.status === "error" && !savedProfile && (
          <section className="profile-card profile-load-error" role="alert">
            <h2>We couldn’t load your profile</h2>
            <p>{loadState.error?.message}</p>
            <button
              className="profile-primary-button"
              onClick={() => void loadProfile()}
            >
              Try again
            </button>
          </section>
        )}
        {savedProfile && draft && (
          <ProfileForm
            profile={savedProfile}
            draft={draft}
            avatarPreview={avatarPreview}
            avatarInputRef={avatarInputRef}
            avatarError={avatarError}
            errors={errors}
            dirty={dirty}
            saving={saveState.status === "pending"}
            saveError={saveState.error?.message ?? ""}
            exporting={exporting}
            avatarUploadSupported={avatarUploadSupported}
            profilePersistence={
              profileService.capabilities?.persistence ?? "local"
            }
            onDraftChange={updateDraft}
            onAvatarChange={selectAvatar}
            onSubmit={(event) => void saveProfile(event)}
            onReset={resetProfile}
            onExport={() => void exportProfile()}
          />
        )}
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
    </div>
  )
}

function ProfileLoadingState() {
  return (
    <section
      className="profile-card profile-loading-card"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="route-loading-indicator" aria-hidden="true" />
      <h2>Loading your local profile</h2>
      <p>Retrieving presentation preferences from the mock profile service…</p>
    </section>
  )
}

function toDraft(profile: UserProfile): UpdateProfileRequestDto {
  return {
    displayName: profile.displayName,
    handle: profile.handle,
    preferredName: profile.displayName,
    role: profile.role,
    about: profile.about,
    preferredLanguage: profile.preferredLanguage,
    responsePreference: profile.responsePreference,
  }
}

function validateProfile(
  profile: UpdateProfileRequestDto,
): ProfileValidationErrors {
  const errors: ProfileValidationErrors = {}
  if (!profile.displayName.trim()) {
    errors.displayName = "Display name is required."
  }
  if (!HANDLE_PATTERN.test(profile.handle)) {
    errors.handle =
      "Use only letters, numbers, underscores, periods, and hyphens."
  }
  if (profile.about.length > ABOUT_LIMIT) {
    errors.about = `About me must be ${ABOUT_LIMIT} characters or fewer.`
  }
  return errors
}
