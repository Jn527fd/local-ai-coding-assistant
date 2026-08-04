export type MutationMode = "optimistic" | "pessimistic" | "acknowledged"

export interface MutationPolicy {
  mode: MutationMode
  rollback: string
}

export type MutationOperation = "auth.signIn" | "auth.signOut" | "auth.requestEmailVerification" | "auth.verifyEmailCode" | "auth.createAccount" | "conversations.create" | "conversations.rename" | "conversations.delete" | "conversations.updateConfiguration" | "messages.send" | "messages.cancel" | "messages.retry" | "sources.upload" | "sources.delete" | "sources.retry" | "profile.update" | "profile.uploadAvatar"

/**
 * Central mutation behavior contract. Backend adapters and UI workflows should
 * preserve these policies when the in-memory mock is replaced.
 */
export const mutationPolicies: Record<MutationOperation, MutationPolicy> = {
  "auth.signIn": {
    mode: "pessimistic",
    rollback: "Keep the unauthenticated session and submitted username.",
  },
  "auth.signOut": {
    mode: "pessimistic",
    rollback: "Clear the local session in finally so credentials never linger.",
  },
  "auth.requestEmailVerification": {
    mode: "pessimistic",
    rollback: "Remain on the email step and preserve the email address.",
  },
  "auth.verifyEmailCode": {
    mode: "pessimistic",
    rollback: "Remain on verification and preserve the entered code.",
  },
  "auth.createAccount": {
    mode: "pessimistic",
    rollback: "Remain on password creation without clearing the fields.",
  },
  "conversations.create": {
    mode: "pessimistic",
    rollback: "Keep the new-conversation draft until the server returns an ID.",
  },
  "conversations.rename": {
    mode: "pessimistic",
    rollback: "Keep the previous title and the editable draft.",
  },
  "conversations.delete": {
    mode: "pessimistic",
    rollback: "Keep the conversation selected and leave the dialog open.",
  },
  "conversations.updateConfiguration": {
    mode: "optimistic",
    rollback: "Restore the prior conversation configuration on failure.",
  },
  "messages.send": {
    mode: "acknowledged",
    rollback:
      "Preserve composer input until the accepted stream event arrives.",
  },
  "messages.cancel": {
    mode: "pessimistic",
    rollback: "Keep the current streaming status when cancellation fails.",
  },
  "messages.retry": {
    mode: "optimistic",
    rollback: "Restore the failed message with the normalized retry error.",
  },
  "sources.upload": {
    mode: "pessimistic",
    rollback: "Keep existing sources and expose the upload error.",
  },
  "sources.delete": {
    mode: "pessimistic",
    rollback: "Keep the source and every scoped selection unchanged.",
  },
  "sources.retry": {
    mode: "optimistic",
    rollback: "Mark the source failed again with the normalized error.",
  },
  "profile.update": {
    mode: "pessimistic",
    rollback:
      "Keep the editable profile draft and display the normalized error.",
  },
  "profile.uploadAvatar": {
    mode: "pessimistic",
    rollback: "Keep the local avatar preview so the user can retry saving.",
  },
}
