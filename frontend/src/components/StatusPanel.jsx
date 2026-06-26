import { useCallback, useEffect, useState } from "react";

import { checkHealth } from "../api.js";
import { Button } from "./ui.jsx";

function StatusPanel({ activeModel, apiBaseUrl }) {
  const [status, setStatus] = useState("checking");
  const [message, setMessage] = useState("Checking backend connection...");

  const refreshStatus = useCallback(async () => {
    setStatus("checking");
    setMessage("Checking backend connection...");

    try {
      const result = await checkHealth();
      if (result?.status === "ok") {
        setStatus("online");
        setMessage("FastAPI is online");
      } else {
        setStatus("offline");
        setMessage("Backend returned an unexpected response");
      }
    } catch (error) {
      setStatus("offline");
      setMessage(error.message);
    }
  }, []);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  return (
    <section className="panel status-panel">
      <div className="panel__heading">
        <div>
          <p className="section-kicker">System</p>
          <h2>Status</h2>
        </div>
        <Button
          className="icon-button"
          onClick={refreshStatus}
          title="Refresh backend status"
          type="button"
          variant="ghost"
        >
          Refresh
        </Button>
      </div>

      <div className={`status-card status-card--${status}`}>
        <span className="status-card__dot" />
        <div>
          <strong>
            {status === "checking"
              ? "Checking"
              : status === "online"
                ? "Connected"
                : "Offline"}
          </strong>
          <p>{message}</p>
        </div>
      </div>

      <dl className="detail-list">
        <div>
          <dt>Backend</dt>
          <dd>{apiBaseUrl}</dd>
        </div>
        <div>
          <dt>Active model</dt>
          <dd>{activeModel || "Checking..."}</dd>
        </div>
      </dl>
    </section>
  );
}

export default StatusPanel;
