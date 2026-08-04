export type AppErrorCode = "validation" | "unauthorized" | "forbidden" | "not_found" | "conflict" | "rate_limited" | "offline" | "timeout" | "server" | "unknown"

export class AppError extends Error {
  readonly code: AppErrorCode
  readonly status?: number
  readonly requestId?: string
  readonly cause?: unknown

  constructor(
    message: string,
    options: {
      code?: AppErrorCode
      status?: number
      requestId?: string
      cause?: unknown
    } = {},
  ) {
    super(message)
    this.name = "AppError"
    this.code = options.code ?? "unknown"
    this.status = options.status
    this.requestId = options.requestId
    this.cause = options.cause
  }
}

export function normalizeError(error: unknown): AppError {
  if (error instanceof AppError) return error
  if (error instanceof DOMException && error.name === "AbortError") {
    return new AppError("The request was cancelled.", {
      code: "timeout",
      cause: error,
    })
  }
  if (typeof navigator !== "undefined" && navigator.onLine === false) {
    return new AppError("You appear to be offline. Check your connection.", {
      code: "offline",
      cause: error,
    })
  }
  if (isErrorWithStatus(error)) {
    return new AppError(
      typeof error.message === "string"
        ? error.message
        : messageForStatus(error.status),
      { code: codeForStatus(error.status), status: error.status, cause: error },
    )
  }
  if (error instanceof Error) {
    return new AppError(error.message, { cause: error })
  }
  return new AppError("An unexpected error occurred.", { cause: error })
}

export function validationError(message: string): AppError {
  return new AppError(message, { code: "validation", status: 422 })
}

function isErrorWithStatus(
  error: unknown,
): error is {
  status: number
  message?: string
} {
  return (
    typeof error === "object" &&
    error !== null &&
    "status" in error &&
    typeof error.status === "number"
  )
}

function codeForStatus(status: number): AppErrorCode {
  if (status === 400 || status === 422) return "validation"
  if (status === 401) return "unauthorized"
  if (status === 403) return "forbidden"
  if (status === 404) return "not_found"
  if (status === 409) return "conflict"
  if (status === 429) return "rate_limited"
  if (status === 408 || status === 504) return "timeout"
  if (status >= 500) return "server"
  return "unknown"
}

function messageForStatus(status: number): string {
  const labels: Partial<Record<AppErrorCode, string>> = {
    validation: "The request contains invalid information.",
    unauthorized: "Sign in to continue.",
    forbidden: "You do not have permission to do that.",
    not_found: "The requested item was not found.",
    conflict: "The request conflicts with the current state.",
    rate_limited: "Too many requests. Try again shortly.",
    timeout: "The request timed out. Try again.",
    server: "The server could not complete the request.",
  }
  return labels[codeForStatus(status)] ?? "The request could not be completed."
}
