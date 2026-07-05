import { useCallback, useEffect, useState } from "react";

import { getDiagnosticsStatus, getSupportBundle } from "../api.js";
import { Button, Card } from "./ui.jsx";

function DiagnosticsPanel({ apiKey }) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [exportMessage, setExportMessage] = useState("");

  const refresh = useCallback(async () => {
    if (!apiKey) {
      setError("Save an API key before loading diagnostics.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      setStatus(await getDiagnosticsStatus(apiKey));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }, [apiKey]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function exportBundle() {
    if (!apiKey) {
      setError("Save an API key before exporting diagnostics.");
      return;
    }
    setBusy(true);
    setExportMessage("");
    setError("");
    try {
      const bundle = await getSupportBundle(apiKey);
      const blob = new Blob([JSON.stringify(bundle, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "local-ai-support-bundle.json";
      link.click();
      URL.revokeObjectURL(url);
      setExportMessage("Redacted support bundle exported.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  const runtime = status?.runtime || {};
  const models = status?.models || {};
  const documents = status?.documents || {};
  const retrieval = status?.retrieval || {};
  const jobs = status?.jobs || {};

  return (
    <section className="diagnostics-panel" aria-label="Diagnostics">
      <div className="panel__heading">
        <div>
          <p className="section-kicker">Diagnostics</p>
          <h2>Runtime overview</h2>
        </div>
        <div className="inline-actions">
          <Button disabled={busy} onClick={refresh} type="button" variant="secondary">
            {busy ? "Refreshing..." : "Refresh"}
          </Button>
          <Button disabled={busy} onClick={exportBundle} type="button" variant="secondary">
            Export bundle
          </Button>
        </div>
      </div>

      {error && <div className="alert alert--error">{error}</div>}
      {exportMessage && <div className="alert alert--success">{exportMessage}</div>}

      <div className="diagnostics-grid">
        <DiagnosticCard
          title="Runtime"
          rows={[
            ["Version", runtime.appVersion || "Unknown"],
            ["Environment", runtime.environment || "Unknown"],
            ["Persistent login", runtime.persistentLoginConfigured ? "Configured" : "In-memory"],
            ["Vector backend", runtime.vectorStoreBackend || "json"],
          ]}
        />
        <DiagnosticCard
          title="Models"
          rows={[
            ["Ollama", models.ollamaConnected ? "Connected" : "Offline"],
            ["Active model", models.activeModel || "None"],
            ["Installed models", models.installedModelCount ?? 0],
            ["Phase", models.phase || "Unknown"],
          ]}
        />
        <DiagnosticCard
          title="Documents"
          rows={[
            ["Documents", documents.documentCount ?? 0],
            ["Conversations", documents.conversationCount ?? 0],
            ["Chunks", documents.chunkCount ?? 0],
            ["Warnings", documents.warningCount ?? 0],
          ]}
        />
        <DiagnosticCard
          title="Retrieval"
          rows={[
            ["Selected backend", retrieval.selectedBackend || "Unknown"],
            ["Fallback", retrieval.fallbackUsed ? "Yes" : "No"],
            ["Top K", retrieval.ragTopK ?? "Unknown"],
            ["Candidate K", retrieval.ragCandidateK ?? "Unknown"],
          ]}
        />
        <DiagnosticCard
          title="Jobs"
          rows={[
            ["Recent jobs", jobs.recentJobCount ?? 0],
            ["States", formatCounts(jobs.stateCounts)],
            ["Types", formatCounts(jobs.typeCounts)],
            ["Failures", jobs.latestFailures?.length ?? 0],
          ]}
        />
      </div>
    </section>
  );
}

function DiagnosticCard({ rows, title }) {
  return (
    <Card className="diagnostics-card">
      <h3>{title}</h3>
      <dl className="detail-list">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}

function formatCounts(counts = {}) {
  const entries = Object.entries(counts);
  if (entries.length === 0) {
    return "None";
  }
  return entries.map(([key, value]) => `${key}: ${value}`).join(", ");
}

export default DiagnosticsPanel;
