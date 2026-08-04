import { useCallback, useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { appServices, type DiagnosticsService } from "../../services"
import type { DiagnosticsStatus } from "../../services/contracts"
import { normalizeError } from "../../services/errors"

const REDACTION_MESSAGE =
  "Support bundles are redacted by default and omit secrets, tokens, cookies, sessions, CSRF values, prompts, chat text, document contents, OCR text, and private file paths."

export function DiagnosticsPage({
  diagnosticsService = appServices.diagnostics,
}: {
  diagnosticsService?: DiagnosticsService
}) {
  const [status, setStatus] = useState<DiagnosticsStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [notice, setNotice] = useState("")
  const [error, setError] = useState("")

  const loadStatus = useCallback(async () => {
    setLoading(true)
    setError("")
    try {
      setStatus(await diagnosticsService.getStatus())
    } catch (caught) {
      setError(normalizeError(caught).message)
    } finally {
      setLoading(false)
    }
  }, [diagnosticsService])

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void loadStatus()
    }, 0)
    return () => window.clearTimeout(handle)
  }, [loadStatus])

  const handleExport = async () => {
    setExporting(true)
    setError("")
    setNotice("")
    try {
      const bundle = await diagnosticsService.exportSupportBundle()
      downloadTextFile(bundle.filename, bundle.mediaType, bundle.content)
      setNotice("Redacted support bundle exported.")
    } catch (caught) {
      setError(normalizeError(caught).message)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="profile-page-shell">
      <header className="profile-topbar">
        <Link to="/chat" className="profile-brand" aria-label="LocalChat home">
          <span aria-hidden="true">LC</span>
          LocalChat
        </Link>
        <Link to="/chat" className="profile-back-link">
          Back to chat
        </Link>
      </header>

      <main id="diagnostics-main" className="profile-main" tabIndex={-1}>
        <div className="profile-page-heading">
          <span className="profile-page-kicker">Local diagnostics</span>
          <h1>Diagnostics</h1>
          <p>Review runtime health and export redacted metadata for support.</p>
        </div>

        <section className="profile-card diagnostics-actions">
          <div>
            <h2>Support bundle</h2>
            <p>{REDACTION_MESSAGE}</p>
          </div>
          <div className="diagnostics-button-row">
            <button
              type="button"
              className="profile-secondary-button"
              onClick={() => void loadStatus()}
              disabled={loading}
            >
              {loading ? "Refreshing..." : "Refresh status"}
            </button>
            <button
              type="button"
              className="profile-primary-button"
              onClick={() => void handleExport()}
              disabled={exporting}
            >
              {exporting ? "Exporting..." : "Export bundle"}
            </button>
          </div>
        </section>

        {error && (
          <section className="profile-card profile-load-error" role="alert">
            <h2>Diagnostics request failed</h2>
            <p>{error}</p>
          </section>
        )}

        {notice && (
          <section className="profile-card diagnostics-notice" role="status">
            {notice}
          </section>
        )}

        <section className="profile-card diagnostics-grid">
          {loading && <p>Loading diagnostics...</p>}
          {!loading && status && (
            <>
              <DiagnosticsCard title="Runtime" value={status.runtime} />
              <DiagnosticsCard title="Models" value={status.models} />
              <DiagnosticsCard title="Documents" value={status.documents} />
              <DiagnosticsCard title="Retrieval" value={status.retrieval} />
              <DiagnosticsCard title="Jobs" value={status.jobs} />
              <DiagnosticsWarnings warnings={status.warnings ?? []} />
            </>
          )}
        </section>
      </main>
    </div>
  )
}

function DiagnosticsCard({
  title,
  value,
}: {
  title: string
  value?: Record<string, unknown>
}) {
  return (
    <article className="diagnostics-card">
      <h2>{title}</h2>
      <pre>{formatDiagnosticValue(value ?? {})}</pre>
    </article>
  )
}

function DiagnosticsWarnings({ warnings }: { warnings: string[] }) {
  if (warnings.length === 0) return null
  return (
    <article className="diagnostics-card diagnostics-warnings">
      <h2>Warnings</h2>
      <ul>
        {warnings.map((warning) => (
          <li key={warning}>{warning}</li>
        ))}
      </ul>
    </article>
  )
}

function formatDiagnosticValue(value: Record<string, unknown>): string {
  return JSON.stringify(value, null, 2)
}

function downloadTextFile(
  filename: string,
  mediaType: string,
  content: string,
) {
  const blob = new Blob([content], { type: mediaType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
