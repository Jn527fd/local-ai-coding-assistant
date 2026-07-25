import type { ChangeEvent, FormEvent, RefObject } from "react"
import type { UpdateProfileRequestDto } from "../../domain/dtos"
import type { UserProfile } from "../../domain/models"

export const ABOUT_LIMIT = 500

export interface ProfileValidationErrors {
  displayName?: string
  handle?: string
  about?: string
}

export function ProfileForm({
  profile,
  draft,
  avatarPreview,
  avatarInputRef,
  avatarError,
  errors,
  dirty,
  saving,
  saveError,
  exporting,
  avatarUploadSupported,
  profilePersistence,
  onDraftChange,
  onAvatarChange,
  onSubmit,
  onReset,
  onExport,
}: {
  profile: UserProfile
  draft: UpdateProfileRequestDto
  avatarPreview: string | null
  avatarInputRef: RefObject<HTMLInputElement | null>
  avatarError: string
  errors: ProfileValidationErrors
  dirty: boolean
  saving: boolean
  saveError: string
  exporting: boolean
  avatarUploadSupported: boolean
  profilePersistence: "backend" | "local"
  onDraftChange: <Key extends keyof UpdateProfileRequestDto,>(
    key: Key,
    value: UpdateProfileRequestDto[Key],
  ) => void
  onAvatarChange: (event: ChangeEvent<HTMLInputElement>) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
  onReset: () => void
  onExport: () => void
}) {
  const initials = profile.displayName
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase()

  return (
    <form className="profile-form" onSubmit={onSubmit} noValidate>
      <section className="profile-card profile-identity-card">
        <div className="profile-avatar-wrap">
          <div
            className="profile-avatar"
            role="img"
            aria-label="Avatar preview"
          >
            {avatarPreview ? (
              <img src={avatarPreview} alt="Profile avatar preview" />
            ) : (
              <span aria-hidden="true">{initials}</span>
            )}
          </div>
          <div>
            <input
              ref={avatarInputRef}
              type="file"
              hidden
              accept="image/png,image/jpeg,image/webp"
              onChange={onAvatarChange}
              aria-describedby="avatar-help avatar-error"
              disabled={!avatarUploadSupported}
            />
            <button
              type="button"
              className="profile-secondary-button"
              onClick={() => avatarInputRef.current?.click()}
              disabled={!avatarUploadSupported}
            >
              Change avatar
            </button>
            <p id="avatar-help" className="profile-field-hint">
              {avatarUploadSupported
                ? "PNG, JPEG, or WebP. Maximum 2 MB."
                : "Avatar upload is not supported by the current backend."}
            </p>
            {avatarError && (
              <p id="avatar-error" className="profile-field-error" role="alert">
                {avatarError}
              </p>
            )}
          </div>
        </div>

        <div className="profile-section-heading">
          <div>
            <h2>Profile details</h2>
            <p>
              These presentation preferences are saved{" "}
              {profilePersistence === "backend"
                ? "by the backend."
                : "in this browser."}
            </p>
          </div>
        </div>

        <div className="profile-fields-grid">
          <ProfileField
            label="Display name"
            htmlFor="profile-display-name"
            error={errors.displayName}
          >
            <input
              id="profile-display-name"
              value={draft.displayName}
              onChange={(event) =>
                onDraftChange("displayName", event.target.value)
              }
              aria-invalid={Boolean(errors.displayName)}
              aria-describedby={
                errors.displayName ? "profile-display-name-error" : undefined
              }
              autoComplete="name"
            />
          </ProfileField>

          <ProfileField
            label="Handle"
            htmlFor="profile-handle"
            error={errors.handle}
          >
            <div className="profile-handle-input">
              <span aria-hidden="true">@</span>
              <input
                id="profile-handle"
                value={draft.handle}
                onChange={(event) =>
                  onDraftChange("handle", event.target.value)
                }
                aria-invalid={Boolean(errors.handle)}
                aria-describedby={
                  errors.handle ? "profile-handle-error" : "profile-handle-help"
                }
                autoComplete="username"
              />
            </div>
            {!errors.handle && (
              <span id="profile-handle-help" className="profile-field-hint">
                Letters, numbers, underscores, periods, and hyphens.
              </span>
            )}
          </ProfileField>

          <ProfileField label="Role or team" htmlFor="profile-role">
            <input
              id="profile-role"
              value={draft.role}
              onChange={(event) => onDraftChange("role", event.target.value)}
              autoComplete="organization-title"
            />
          </ProfileField>

          <ProfileField label="Preferred language" htmlFor="profile-language">
            <select
              id="profile-language"
              value={draft.preferredLanguage}
              onChange={(event) =>
                onDraftChange("preferredLanguage", event.target.value)
              }
            >
              <option value="en-US">English (United States)</option>
              <option value="en-GB">English (United Kingdom)</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="de">German</option>
              <option value="ja">Japanese</option>
            </select>
          </ProfileField>

          <ProfileField
            label="About me"
            htmlFor="profile-about"
            error={errors.about}
            wide
          >
            <textarea
              id="profile-about"
              value={draft.about}
              maxLength={ABOUT_LIMIT + 1}
              rows={5}
              onChange={(event) => onDraftChange("about", event.target.value)}
              aria-invalid={Boolean(errors.about)}
              aria-describedby="profile-about-count profile-about-error"
            />
            <span
              id="profile-about-count"
              className={`profile-character-count${
                errors.about ? " is-error" : ""
              }`}
            >
              {draft.about.length}/{ABOUT_LIMIT}
            </span>
          </ProfileField>
        </div>
      </section>

      <section className="profile-card" aria-labelledby="local-account-title">
        <div className="profile-section-heading">
          <div>
            <h2 id="local-account-title">Local account information</h2>
            <p>Read-only details assigned by this LocalChat network.</p>
          </div>
          <span className="profile-readonly-badge">Read only</span>
        </div>
        <dl className="profile-account-grid">
          <AccountDetail label="User ID" value={profile.id} mono />
          <AccountDetail
            label="Account type"
            value={capitalize(profile.accountType)}
          />
          <AccountDetail label="Device name" value={profile.deviceName} />
          <AccountDetail
            label="Joined network"
            value={formatJoinedDate(profile.joinedAt)}
          />
          <AccountDetail
            label="Data storage location"
            value={profile.storageLocation}
            wide
          />
        </dl>
        <p className="profile-field-hint">
          Backend account fields come from the local server. Editable profile
          preferences are browser-local until a backend profile API is added.
        </p>
        <div className="profile-privacy-note">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"
              stroke="currentColor"
              strokeWidth="1.8"
            />
            <path
              d="M9.5 12l1.6 1.6 3.7-4"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <p>
            Your profile is stored on this network’s local server. Visibility
            and retention depend on the server administrator’s configuration.
          </p>
        </div>
      </section>

      <section
        className="profile-card profile-actions-card"
        aria-labelledby="profile-actions-title"
      >
        <div>
          <h2 id="profile-actions-title">Your profile data</h2>
          <p>Download a copy of your local profile data.</p>
        </div>
        <div className="profile-data-actions">
          <button
            type="button"
            className="profile-secondary-button"
            onClick={onExport}
            disabled={exporting}
          >
            {exporting ? "Preparing export…" : "Export my data"}
          </button>
        </div>
      </section>

      {saveError && (
        <p className="profile-save-error" role="alert">
          {saveError}
        </p>
      )}

      <div className="profile-sticky-actions">
        <p aria-live="polite">
          {dirty ? "You have unsaved changes." : "All changes are saved."}
        </p>
        <div>
          <button
            type="button"
            className="profile-secondary-button"
            onClick={onReset}
            disabled={!dirty || saving}
          >
            Reset
          </button>
          <button
            type="submit"
            className="profile-primary-button"
            disabled={!dirty || saving || Boolean(Object.keys(errors).length)}
          >
            {saving && <span className="button-spinner" aria-hidden="true" />}
            {saving ? "Saving…" : "Save changes"}
          </button>
        </div>
      </div>
    </form>
  )
}

function ProfileField({
  label,
  htmlFor,
  error,
  wide = false,
  children,
}: {
  label: string
  htmlFor: string
  error?: string
  wide?: boolean
  children: React.ReactNode
}) {
  return (
    <div className={`profile-field${wide ? " profile-field-wide" : ""}`}>
      <label htmlFor={htmlFor}>{label}</label>
      {children}
      {error && (
        <span id={`${htmlFor}-error`} className="profile-field-error">
          {error}
        </span>
      )}
    </div>
  )
}

function AccountDetail({
  label,
  value,
  mono = false,
  wide = false,
}: {
  label: string
  value: string
  mono?: boolean
  wide?: boolean
}) {
  return (
    <div className={wide ? "profile-account-wide" : undefined}>
      <dt>{label}</dt>
      <dd className={mono ? "profile-mono" : undefined}>{value}</dd>
    </div>
  )
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

function formatJoinedDate(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "Unknown"
  return new Intl.DateTimeFormat(undefined, {
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(date)
}
