import { useCallback, useState } from "react";

export const API_KEY_STORAGE_KEY = "local-ai-coding-assistant.api-key";

export function useStoredApiKey(storageKey = API_KEY_STORAGE_KEY) {
  const [apiKey, setApiKeyState] = useState(
    () => window.localStorage.getItem(storageKey) || "",
  );

  const setApiKey = useCallback(
    (nextKey) => {
      setApiKeyState(nextKey);
      window.localStorage.setItem(storageKey, nextKey);
    },
    [storageKey],
  );

  return { apiKey, setApiKey };
}
