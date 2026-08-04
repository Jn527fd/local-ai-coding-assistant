import { AppError, normalizeError, type AppErrorCode } from "../services/errors"

export interface ApiClientOptions {
  baseUrl: string
  getAccessToken?: () => string | null
  fetchImplementation?: typeof fetch
  csrfCookieName?: string
  credentials?: RequestCredentials
}

export interface ApiRequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown
  formData?: FormData
}

export interface ApiClient {
  request<Response>(
    path: string,
    options?: ApiRequestOptions,
  ): Promise<Response>
}

export function createApiClient({
  baseUrl,
  getAccessToken = () => null,
  fetchImplementation = fetch,
  csrfCookieName = "local_ai_csrf",
  credentials = "include",
}: ApiClientOptions): ApiClient {
  return {
    async request<Response,>(
      path: string,
      options: ApiRequestOptions = {},
    ): Promise<Response> {
      const requestId = createRequestId()
      const headers = new Headers(options.headers)
      headers.set("Accept", "application/json")
      headers.set("X-Request-ID", requestId)

      const token = getAccessToken()
      if (token) headers.set("Authorization", `Bearer ${token}`)

      const method = (options.method ?? "GET").toUpperCase()
      if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
        const csrfToken = readCookie(csrfCookieName)
        if (csrfToken) headers.set("X-CSRF-Token", csrfToken)
      }

      let body: BodyInit | undefined
      if (options.formData !== undefined) {
        body = options.formData
      } else if (options.body !== undefined) {
        headers.set("Content-Type", "application/json")
        body = JSON.stringify(options.body)
      }

      try {
        const response = await fetchImplementation(resolveUrl(baseUrl, path), {
          ...options,
          credentials,
          headers,
          body,
          signal: options.signal,
        })

        if (!response.ok) {
          throw await createHttpError(response, requestId)
        }

        if (response.status === 204) return undefined as Response
        const responseText = await response.text()
        if (!responseText) return undefined as Response
        return JSON.parse(responseText) as Response
      } catch (error) {
        const normalized = normalizeError(error)
        if (normalized.requestId) throw normalized
        throw new AppError(normalized.message, {
          code: normalized.code,
          status: normalized.status,
          requestId,
          cause: normalized.cause,
        })
      }
    },
  }
}

function resolveUrl(baseUrl: string, path: string): string {
  return `${baseUrl.replace(/\/$/, "")}/${path.replace(/^\//, "")}`
}

function createRequestId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `request-${Date.now()}`
}

async function createHttpError(
  response: Response,
  requestId: string,
): Promise<AppError> {
  const responseText = await response.text().catch(() => "")
  const errorBody = parseJsonOrText(responseText)
  const message = errorMessageFromBody(errorBody, response.status)

  return new AppError(message, {
    code: statusToErrorCode(response.status),
    status: response.status,
    requestId: response.headers.get("X-Request-ID") ?? requestId,
  })
}

function parseJsonOrText(text: string): unknown {
  if (!text) return null
  try {
    return JSON.parse(text) as unknown
  } catch {
    return text
  }
}

function errorMessageFromBody(body: unknown, status: number): string {
  if (typeof body === "string" && body) return body
  if (typeof body !== "object" || body === null) {
    return `Request failed with status ${status}.`
  }

  if (
    "message" in body &&
    typeof (body as { message?: unknown }).message === "string"
  ) {
    return (body as { message: string }).message
  }

  if ("detail" in body) {
    return errorMessageFromDetail((body as { detail: unknown }).detail, status)
  }

  return `Request failed with status ${status}.`
}

function errorMessageFromDetail(detail: unknown, status: number): string {
  if (typeof detail === "string" && detail) return detail
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (
          typeof item !== "object" ||
          item === null ||
          !("msg" in item) ||
          typeof (item as { msg?: unknown }).msg !== "string"
        ) {
          return ""
        }
        const location =
          "loc" in item && Array.isArray((item as { loc?: unknown }).loc)
            ? (item as { loc: unknown[] }).loc
                .filter((part) => part !== "body")
                .join(".")
            : ""
        return location
          ? `${location}: ${(item as { msg: string }).msg}`
          : (item as { msg: string }).msg
      })
      .filter(Boolean)
    if (messages.length > 0) return messages.join(" ")
  }
  return `Request failed with status ${status}.`
}

function readCookie(name: string): string {
  if (typeof document === "undefined" || !document.cookie) return ""
  const value = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${name}=`))
    ?.slice(name.length + 1)
  return value ? decodeURIComponent(value) : ""
}

function statusToErrorCode(status: number): AppErrorCode {
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
