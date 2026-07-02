import { useCallback, useState } from "react";

import { getComponentCapabilities } from "../api.js";

const IDLE_STATUS = {
  status: "idle",
  message: "",
};

const CHECKING_STATUS = {
  status: "checking",
  message: "Checking local models and tools...",
};

const READY_STATUS = {
  status: "ready",
  message: "Local models and tools refreshed.",
};

export function useCapabilities() {
  const [capabilities, setCapabilities] = useState(null);
  const [capabilitiesStatus, setCapabilitiesStatus] = useState(IDLE_STATUS);

  const refreshCapabilities = useCallback(async () => {
    setCapabilitiesStatus(CHECKING_STATUS);

    try {
      const result = await getComponentCapabilities();
      setCapabilities(result);
      setCapabilitiesStatus(READY_STATUS);
      return result;
    } catch (error) {
      setCapabilitiesStatus({
        status: "error",
        message: error.message,
      });
      return null;
    }
  }, []);

  const resetCapabilities = useCallback(() => {
    setCapabilities(null);
    setCapabilitiesStatus(IDLE_STATUS);
  }, []);

  return {
    capabilities,
    capabilitiesStatus,
    refreshCapabilities,
    resetCapabilities,
  };
}
