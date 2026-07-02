import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getComponentCapabilities } from "../api.js";
import { useCapabilities } from "./useCapabilities.js";

vi.mock("../api.js", () => ({
  getComponentCapabilities: vi.fn(),
}));

describe("useCapabilities", () => {
  beforeEach(() => {
    getComponentCapabilities.mockReset();
  });

  it("starts idle with no capabilities", () => {
    const { result } = renderHook(() => useCapabilities());

    expect(result.current.capabilities).toBeNull();
    expect(result.current.capabilitiesStatus).toEqual({
      status: "idle",
      message: "",
    });
  });

  it("refreshes capabilities and reports ready status", async () => {
    const capabilities = {
      llmModels: [{ id: "llama3", available: true }],
    };
    getComponentCapabilities.mockResolvedValueOnce(capabilities);
    const { result } = renderHook(() => useCapabilities());

    let refreshed;
    await act(async () => {
      refreshed = await result.current.refreshCapabilities();
    });

    expect(refreshed).toBe(capabilities);
    expect(result.current.capabilities).toBe(capabilities);
    expect(result.current.capabilitiesStatus).toEqual({
      status: "ready",
      message: "Local models and tools refreshed.",
    });
  });

  it("reports loading status while refresh is pending", async () => {
    let resolveCapabilities;
    getComponentCapabilities.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveCapabilities = resolve;
      }),
    );
    const { result } = renderHook(() => useCapabilities());

    let refreshPromise;
    act(() => {
      refreshPromise = result.current.refreshCapabilities();
    });

    expect(result.current.capabilitiesStatus).toEqual({
      status: "checking",
      message: "Checking local models and tools...",
    });

    await act(async () => {
      resolveCapabilities({ llmModels: [] });
      await refreshPromise;
    });
  });

  it("keeps the app usable when capabilities refresh fails", async () => {
    getComponentCapabilities.mockRejectedValueOnce(new Error("network offline"));
    const { result } = renderHook(() => useCapabilities());

    let refreshed;
    await act(async () => {
      refreshed = await result.current.refreshCapabilities();
    });

    expect(refreshed).toBeNull();
    expect(result.current.capabilities).toBeNull();
    expect(result.current.capabilitiesStatus).toEqual({
      status: "error",
      message: "network offline",
    });
  });

  it("resets capability state", async () => {
    const capabilities = {
      llmModels: [{ id: "llama3", available: true }],
    };
    getComponentCapabilities.mockResolvedValueOnce(capabilities);
    const { result } = renderHook(() => useCapabilities());

    await act(async () => {
      await result.current.refreshCapabilities();
    });
    act(() => {
      result.current.resetCapabilities();
    });

    expect(result.current.capabilities).toBeNull();
    expect(result.current.capabilitiesStatus).toEqual({
      status: "idle",
      message: "",
    });
  });
});
