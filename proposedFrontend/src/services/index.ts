import type { AppServices } from "./contracts"
import { apiClient, type ApiClient } from "../api"
import { createHttpServices } from "./http/createHttpServices"
import { createMockServices } from "./mock/createMockServices"
import type { MockServiceControl } from "./mock/createMockServices"

export interface AppServiceSelectionOptions {
  useMockApi?: unknown
  client?: ApiClient
}

export interface AppServiceSelection {
  services: AppServices
  mockControl: MockServiceControl | null
}

export function resolveUseMockApi(value: unknown): boolean {
  if (typeof value === "boolean") return value
  if (typeof value === "string") return value.toLowerCase() !== "false"
  return true
}

export function createAppServices({
  useMockApi = import.meta.env.VITE_USE_MOCK_API,
  client = apiClient,
}: AppServiceSelectionOptions = {}): AppServiceSelection {
  if (resolveUseMockApi(useMockApi)) {
    const mockBundle = createMockServices()
    return {
      services: mockBundle.services,
      mockControl: mockBundle.control,
    }
  }
  return {
    services: createHttpServices({ apiClient: client }),
    mockControl: null,
  }
}

const selectedServices = createAppServices()

export const appServices: AppServices = selectedServices.services

// Exported for deterministic development and future automated tests.
// UI modules intentionally import only `appServices`.
export const mockServiceControl = selectedServices.mockControl

export type {
  AppServices,
  AccountService,
  AuthService,
  ConversationService,
  DiagnosticsService,
  MessageService,
  ProfileService,
  RepositoryService,
  SourceService,
} from "./contracts"
export type { AsyncState, AsyncStatus } from "./asyncState"
export {
  errorAsyncState,
  idleAsyncState,
  pendingAsyncState,
  successAsyncState,
} from "./asyncState"
export {
  mutationPolicies,
  type MutationMode,
  type MutationOperation,
  type MutationPolicy,
} from "./mutationPolicies"
