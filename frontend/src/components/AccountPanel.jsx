import { useEffect, useMemo, useState } from "react";

import {
  getAccountStatus,
  getModelStatus,
  switchModel,
  updateApiKey,
} from "../api.js";

function statusClass(isActive) {
  return isActive ? "connection-state--online" : "connection-state--offline";
}

function AccountPanel({
  apiKey,
  isOpen,
  onApiKeyChange,
  onClose,
  onLogout,
  onModelStatus,
  username,
}) {
  const [draftApiKey, setDraftApiKey] = useState(apiKey);
  const [showApiKey, setShowApiKey] = useState(false);
  const [accountStatus, setAccountStatus] = useState(null);
  const [accountError, setAccountError] = useState("");
  const [isSavingKey, setIsSavingKey] = useState(false);
  const [isCheckingKey, setIsCheckingKey] = useState(false);

  const [modelStatus, setModelStatus] = useState(null);
  const [selectedModel, setSelectedModel] = useState("");
  const [modelError, setModelError] = useState("");

  const selectedDefinition = useMemo(
    () =>
      modelStatus?.supported_models.find(
        (model) => model.name === selectedModel,
      ),
    [modelStatus, selectedModel],
  );

  async function refreshAccountStatus(key = draftApiKey) {
    setIsCheckingKey(true);
    setAccountError("");
    try {
      setAccountStatus(await getAccountStatus(key.trim()));
    } catch (requestError) {
      setAccountError(requestError.message);
    } finally {
      setIsCheckingKey(false);
    }
  }

  async function refreshModelStatus() {
    try {
      const status = await getModelStatus();
      setModelStatus(status);
      setSelectedModel((current) => current || status.active_model);
      setModelError(status.error || "");
      onModelStatus(status);
      return status;
    } catch (requestError) {
      setModelError(requestError.message);
      return null;
    }
  }

  useEffect(() => {
    setDraftApiKey(apiKey);
  }, [apiKey]);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    refreshAccountStatus(apiKey);
    refreshModelStatus();
    return undefined;
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || !modelStatus?.switching) {
      return undefined;
    }

    const intervalId = window.setInterval(async () => {
      const status = await refreshModelStatus();
      if (status && !status.switching) {
        await refreshAccountStatus(draftApiKey);
      }
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, [isOpen, modelStatus?.switching, draftApiKey]);

  async function handleSaveApiKey(event) {
    event.preventDefault();
    const trimmedKey = draftApiKey.trim();
    if (trimmedKey.length < 16) {
      setAccountError("Use an API key with at least 16 characters.");
      return;
    }

    setIsSavingKey(true);
    setAccountError("");
    try {
      const status = await updateApiKey(trimmedKey);
      onApiKeyChange(trimmedKey);
      setAccountStatus(status);
    } catch (requestError) {
      setAccountError(requestError.message);
    } finally {
      setIsSavingKey(false);
    }
  }

  async function handleSwitchModel() {
    if (!selectedDefinition || selectedDefinition.parameters_billion > 7) {
      setModelError("Select a supported model with 7B parameters or fewer.");
      return;
    }

    if (selectedModel === modelStatus?.active_model) {
      setModelError("That model is already active.");
      return;
    }

    const confirmed = window.confirm(
      `Switch to ${selectedModel}? After the new model downloads successfully, ` +
        "the previous active model files will be removed.",
    );
    if (!confirmed) {
      return;
    }

    setModelError("");
    try {
      await switchModel(selectedModel);
      await refreshModelStatus();
    } catch (requestError) {
      setModelError(requestError.message);
    }
  }

  if (!isOpen) {
    return null;
  }

  const isSwitching = Boolean(modelStatus?.switching);
  const progress = modelStatus?.progress;

  return (
    <div className="account-overlay" role="presentation" onMouseDown={onClose}>
      <aside
        aria-label="Account and API settings"
        className="account-drawer"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="account-drawer__header">
          <div>
            <p className="section-kicker">Account</p>
            <h2>{username}</h2>
          </div>
          <button className="icon-button" onClick={onClose} type="button">
            Close
          </button>
        </div>

        <section className="account-section">
          <div className="account-section__heading">
            <div>
              <h3>API access</h3>
              <p>Persist the Bearer key used by protected app requests.</p>
            </div>
            <span
              className={`connection-state ${statusClass(
                accountStatus?.api_key_active,
              )}`}
            >
              {accountStatus?.api_key_active ? "Connected" : "Not connected"}
            </span>
          </div>

          <form className="stacked-form" onSubmit={handleSaveApiKey}>
            <label className="field">
              <span className="field__label">Local API key</span>
              <div className="secret-input">
                <input
                  autoComplete="off"
                  onChange={(event) => setDraftApiKey(event.target.value)}
                  placeholder="Enter at least 16 characters"
                  type={showApiKey ? "text" : "password"}
                  value={draftApiKey}
                />
                <button
                  className="text-button"
                  onClick={() => setShowApiKey((current) => !current)}
                  type="button"
                >
                  {showApiKey ? "Hide" : "Show"}
                </button>
              </div>
            </label>

            <div className="inline-actions">
              <button
                className="secondary-button"
                disabled={isSavingKey}
                type="submit"
              >
                {isSavingKey ? "Saving..." : "Save key"}
              </button>
              <button
                className="ghost-button"
                disabled={isCheckingKey}
                onClick={() => refreshAccountStatus()}
                type="button"
              >
                {isCheckingKey ? "Checking..." : "Check connection"}
              </button>
            </div>
          </form>

          <p className="account-note">
            The browser copy is stored in local storage. The active backend
            copy is stored in the ignored local settings file.
          </p>
          {accountError && (
            <div className="alert alert--error">{accountError}</div>
          )}
        </section>

        <section className="account-section">
          <div className="account-section__heading">
            <div>
              <h3>Active model</h3>
              <p>Only approved Ollama models with 7B parameters or fewer.</p>
            </div>
            <span
              className={`connection-state ${statusClass(
                modelStatus?.ollama_connected,
              )}`}
            >
              {modelStatus?.ollama_connected
                ? "Ollama connected"
                : "Ollama offline"}
            </span>
          </div>

          <label className="field">
            <span className="field__label">Model catalog</span>
            <select
              disabled={isSwitching}
              onChange={(event) => setSelectedModel(event.target.value)}
              value={selectedModel}
            >
              {(modelStatus?.supported_models || []).map((model) => (
                <option key={model.name} value={model.name}>
                  {model.label} ({model.parameters_billion}B, about{" "}
                  {model.approximate_download})
                </option>
              ))}
            </select>
          </label>

          <div className="model-summary">
            <span>Current</span>
            <strong>{modelStatus?.active_model || "Checking..."}</strong>
          </div>

          {(isSwitching || modelStatus?.phase === "complete") && (
            <div className="model-progress" aria-live="polite">
              <div className="model-progress__header">
                <span>{modelStatus.message}</span>
                {typeof progress === "number" && <strong>{progress}%</strong>}
              </div>
              <div className="progress-track">
                <span
                  className={
                    typeof progress === "number"
                      ? ""
                      : "progress-track__indeterminate"
                  }
                  style={
                    typeof progress === "number"
                      ? { width: `${progress}%` }
                      : undefined
                  }
                />
              </div>
            </div>
          )}

          {modelStatus?.warning && (
            <div className="alert alert--warning">{modelStatus.warning}</div>
          )}
          {modelError && <div className="alert alert--error">{modelError}</div>}

          <button
            className="secondary-button"
            disabled={
              isSwitching ||
              !selectedModel ||
              selectedModel === modelStatus?.active_model
            }
            onClick={handleSwitchModel}
            type="button"
          >
            {isSwitching ? "Switching model..." : "Install and activate"}
          </button>

          <p className="account-note">
            The old model is unloaded first and deleted only after the new
            download succeeds. Ollama safely manages any shared model layers.
          </p>
        </section>

        <button className="logout-button" onClick={onLogout} type="button">
          Sign out
        </button>
      </aside>
    </div>
  );
}

export default AccountPanel;
