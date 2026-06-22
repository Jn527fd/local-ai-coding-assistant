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

function modelConnectionLabel(modelStatus, modelError) {
  if (!modelStatus) {
    return modelError ? "Status unavailable" : "Checking...";
  }

  return modelStatus.ollama_connected ? "Ollama connected" : "Ollama offline";
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
      setSelectedModel((current) => {
        const modelNames = status.supported_models.map((model) => model.name);
        if (modelNames.includes(current)) {
          return current;
        }
        if (modelNames.includes(status.active_model)) {
          return status.active_model;
        }
        return modelNames[0] || "";
      });
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
    if (!isOpen) {
      return undefined;
    }

    const intervalId = window.setInterval(refreshModelStatus, 5000);

    return () => window.clearInterval(intervalId);
  }, [isOpen]);

  async function handleSaveApiKey(event) {
    event.preventDefault();
    const trimmedKey = draftApiKey.trim();
    if (!trimmedKey) {
      setAccountError("Enter an API key before saving.");
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
    if (!selectedDefinition) {
      setModelError("Select an eligible model installed in Ollama.");
      return;
    }

    if (selectedModel === modelStatus?.active_model) {
      setModelError("That model is already active.");
      return;
    }

    const confirmed = window.confirm(
      `Switch to the installed ${selectedModel} model? Your chats will be retained.`,
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
  const switchButtonLabel = isSwitching
    ? "Switching model..."
    : "Use installed model";

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
                  placeholder="Enter a local API key"
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
            copy is stored in the ignored local settings file. Short keys are
            accepted for local testing; use a longer private key for normal use.
          </p>
          {accountError && (
            <div className="alert alert--error">{accountError}</div>
          )}
        </section>

        <section className="account-section">
          <div className="account-section__heading">
            <div>
              <h3>Active model</h3>
              <p>
                Installed Ollama models with{" "}
                {modelStatus?.max_parameters_billion || 7}B parameters or
                fewer.
              </p>
            </div>
            <span
              className={`connection-state ${statusClass(
                modelStatus?.ollama_connected,
              )}`}
            >
              {modelConnectionLabel(modelStatus, modelError)}
            </span>
          </div>

          <label className="field">
            <span className="field__label">Model catalog</span>
            <select
              disabled={isSwitching || !modelStatus?.supported_models.length}
              onChange={(event) => setSelectedModel(event.target.value)}
              value={selectedModel}
            >
              {!modelStatus?.supported_models.length && (
                <option value="">No eligible local models found</option>
              )}
              {(modelStatus?.supported_models || []).map((model) => (
                <option key={model.name} value={model.name}>
                  {model.label} ({model.parameter_size}, {model.size_display}
                  {model.quantization_level
                    ? `, ${model.quantization_level}`
                    : ""}
                  )
                </option>
              ))}
            </select>
          </label>

          {Boolean(modelStatus?.excluded_model_count) && (
            <p className="account-note">
              {modelStatus.excluded_model_count} installed model
              {modelStatus.excluded_model_count === 1 ? " is" : "s are"} hidden
              because the reported parameter size is above{" "}
              {modelStatus.max_parameters_billion}B or unavailable.
            </p>
          )}

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

          <div className="inline-actions">
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
              {switchButtonLabel}
            </button>
            <button
              className="ghost-button"
              disabled={isSwitching}
              onClick={refreshModelStatus}
              type="button"
            >
              Refresh local models
            </button>
          </div>

          <p className="account-note">
            Pull models with Ollama, then refresh this list. The application
            only selects local models and never downloads or deletes them.
            Switching models does not reset your chats.
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
