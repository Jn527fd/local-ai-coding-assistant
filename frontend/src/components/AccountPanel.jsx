import { useEffect, useMemo, useState } from "react";

import {
  getAccountStatus,
  getModelStatus,
  switchModel,
  updateApiKey,
} from "../api.js";
import { Badge, Button, Card, Input, Select } from "./ui.jsx";

function statusClass(isActive) {
  return isActive ? "connection-state--online" : "connection-state--offline";
}

function modelConnectionLabel(modelStatus, modelError) {
  if (!modelStatus) {
    return modelError ? "Status unavailable" : "Checking...";
  }

  return modelStatus.ollama_connected ? "Ollama connected" : "Ollama offline";
}

function SettingsCard({ actions, badge, children, description, eyebrow, title }) {
  return (
    <Card className="account-section">
      <div className="account-section__heading">
        <div>
          {eyebrow && <span className="settings-card__eyebrow">{eyebrow}</span>}
          <h3>{title}</h3>
          {description && <p>{description}</p>}
        </div>
        {badge || actions ? (
          <div className="settings-card__actions">
            {badge}
            {actions}
          </div>
        ) : null}
      </div>
      {children}
    </Card>
  );
}

function SettingsStatusRow({ detail, label, tone = "neutral", value }) {
  return (
    <div className={`settings-status-row settings-status-row--${tone}`}>
      <span className="settings-status-row__dot" aria-hidden="true" />
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      {detail && <small>{detail}</small>}
    </div>
  );
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
  const [pendingModel, setPendingModel] = useState("");
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
      setModelError("Select a model installed in Ollama.");
      return;
    }

    if (selectedModel === modelStatus?.active_model) {
      setModelError("That model is already active.");
      return;
    }

    setPendingModel(selectedModel);
  }

  async function confirmSwitchModel() {
    if (!pendingModel) {
      return;
    }
    setModelError("");
    try {
      await switchModel(pendingModel);
      setPendingModel("");
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
  const apiConnected = Boolean(accountStatus?.api_key_active);
  const ollamaConnected = Boolean(modelStatus?.ollama_connected);
  const installedModelCount = modelStatus?.supported_models?.length || 0;

  return (
    <div className="account-overlay" role="presentation" onMouseDown={onClose}>
      <aside
        aria-label="Account and API settings"
        className="account-drawer"
        onMouseDown={(event) => event.stopPropagation()}
        role="complementary"
      >
        <div className="account-drawer__header">
          <div>
            <p className="section-kicker">Account</p>
            <h2>{username}</h2>
          </div>
          <Button className="icon-button" onClick={onClose} type="button" variant="ghost">
            Close
          </Button>
        </div>

        <SettingsCard
          badge={
            <Badge className="connection-state" tone={apiConnected && ollamaConnected ? "success" : "warning"}>
              {apiConnected && ollamaConnected ? "Operational" : "Review"}
            </Badge>
          }
          description="Local service health and model readiness at a glance."
          eyebrow="System"
          title="Runtime overview"
        >
          <div className="settings-status-grid">
            <SettingsStatusRow
              detail="Bearer requests"
              label="API key"
              tone={apiConnected ? "success" : "error"}
              value={apiConnected ? "Connected" : "Not connected"}
            />
            <SettingsStatusRow
              detail={ollamaConnected ? "Local model service ready" : modelConnectionLabel(modelStatus, modelError)}
              label="Ollama"
              tone={ollamaConnected ? "success" : "error"}
              value={modelStatus?.active_model || "Checking..."}
            />
            <SettingsStatusRow
              detail={`${installedModelCount} local model${installedModelCount === 1 ? "" : "s"}`}
              label="Model library"
              tone={installedModelCount ? "success" : "warning"}
              value={installedModelCount ? "Available" : "Empty"}
            />
          </div>
        </SettingsCard>

        <SettingsCard
          actions={
            <Button
              className="settings-card__text-action"
              disabled={isCheckingKey}
              onClick={() => refreshAccountStatus()}
              type="button"
              variant="plain"
            >
              {isCheckingKey ? "Checking..." : "Check"}
            </Button>
          }
          badge={
            <Badge
              className={`connection-state ${statusClass(apiConnected)}`}
              tone={apiConnected ? "success" : "error"}
            >
              {apiConnected ? "Connected" : "Not connected"}
            </Badge>
          }
          description="The key stays on this machine and is used for protected local requests."
          eyebrow="Authentication"
          title="API access"
        >

          <form className="stacked-form" onSubmit={handleSaveApiKey}>
            <label className="field">
              <span className="field__label">Local API key</span>
              <div className="secret-input">
                <Input
                  autoComplete="off"
                  onChange={(event) => setDraftApiKey(event.target.value)}
                  placeholder="Enter a local API key"
                  type={showApiKey ? "text" : "password"}
                  value={draftApiKey}
                />
                <Button
                  className="text-button"
                  onClick={() => setShowApiKey((current) => !current)}
                  type="button"
                  variant="plain"
                >
                  {showApiKey ? "Hide" : "Show"}
                </Button>
              </div>
            </label>

            <div className="inline-actions">
              <Button
                className="secondary-button"
                disabled={isSavingKey}
                type="submit"
                variant="secondary"
              >
                {isSavingKey ? "Saving..." : "Save key"}
              </Button>
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
        </SettingsCard>

        <SettingsCard
          actions={
            <Button
              className="settings-card__text-action"
              disabled={isSwitching}
              onClick={refreshModelStatus}
              type="button"
              variant="plain"
            >
              Refresh
            </Button>
          }
          badge={
            <Badge
              className={`connection-state ${statusClass(ollamaConnected)}`}
              tone={ollamaConnected ? "success" : "error"}
            >
              {modelConnectionLabel(modelStatus, modelError)}
            </Badge>
          }
          description="Switch between models already installed in your local Ollama library."
          eyebrow="Models"
          title="Active model"
        >

          <label className="field">
            <span className="field__label">Model catalog</span>
            <Select
              disabled={isSwitching || !modelStatus?.supported_models.length}
              onChange={(event) => {
                setSelectedModel(event.target.value);
                setPendingModel("");
              }}
              value={selectedModel}
            >
              {!modelStatus?.supported_models.length && (
                <option value="">No local models found</option>
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
            </Select>
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
                  aria-label="Model switch progress"
                  className={
                    typeof progress === "number"
                      ? ""
                      : "progress-track__indeterminate"
                  }
                  role="progressbar"
                  aria-valuemax={100}
                  aria-valuemin={0}
                  aria-valuenow={typeof progress === "number" ? progress : undefined}
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

          {pendingModel && (
            <div className="model-confirmation" role="alert">
              <div>
                <strong>Switch active model to {pendingModel}?</strong>
                <p>Your local chat history stays intact. Only the active Ollama model string changes.</p>
              </div>
              <div className="inline-actions">
                <Button
                  className="ghost-button"
                  onClick={() => setPendingModel("")}
                  type="button"
                  variant="ghost"
                >
                  Cancel
                </Button>
                <Button
                  className="secondary-button"
                  disabled={isSwitching}
                  onClick={confirmSwitchModel}
                  type="button"
                  variant="secondary"
                >
                  Confirm switch
                </Button>
              </div>
            </div>
          )}

          <div className="inline-actions">
            <Button
              className="secondary-button"
              disabled={
                isSwitching ||
                !selectedModel ||
                selectedModel === modelStatus?.active_model
              }
              onClick={handleSwitchModel}
              type="button"
              variant="secondary"
            >
              {switchButtonLabel}
            </Button>
          </div>

          <p className="account-note">
            Pull models with Ollama, then refresh this list. The application
            shows every local model Ollama reports and never downloads or
            deletes model files. Switching models does not reset your chats.
          </p>
        </SettingsCard>

        <div className="account-footer">
          <Button className="logout-button" onClick={onLogout} type="button" variant="danger">
            Sign out
          </Button>
        </div>
      </aside>
    </div>
  );
}

export default AccountPanel;
