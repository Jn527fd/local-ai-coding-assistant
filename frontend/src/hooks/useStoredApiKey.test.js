import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { API_KEY_STORAGE_KEY, useStoredApiKey } from "./useStoredApiKey.js";

describe("useStoredApiKey", () => {
  it("loads and persists the API key in localStorage", () => {
    window.localStorage.setItem(API_KEY_STORAGE_KEY, "saved-key");

    const { result } = renderHook(() => useStoredApiKey());

    expect(result.current.apiKey).toBe("saved-key");

    act(() => {
      result.current.setApiKey("next-key");
    });

    expect(result.current.apiKey).toBe("next-key");
    expect(window.localStorage.getItem(API_KEY_STORAGE_KEY)).toBe("next-key");
  });
});
