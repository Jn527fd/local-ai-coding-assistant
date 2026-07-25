import type { AppError } from "./errors"

export type AsyncStatus = "idle" | "pending" | "success" | "error"

export interface AsyncState<T> {
  status: AsyncStatus
  data?: T
  error?: AppError
}

export function idleAsyncState<T>(data?: T): AsyncState<T> {
  return { status: "idle", data }
}

export function pendingAsyncState<T>(data?: T): AsyncState<T> {
  return { status: "pending", data }
}

export function successAsyncState<T>(data: T): AsyncState<T> {
  return { status: "success", data }
}

export function errorAsyncState<T>(error: AppError, data?: T): AsyncState<T> {
  return { status: "error", data, error }
}
