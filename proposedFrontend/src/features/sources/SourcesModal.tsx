import { useRef, type ChangeEvent, type RefObject } from "react"
import { CenteredModal } from "../../components/CenteredModal"
import type { SourceDocument } from "../../domain/models"

export function SourcesModal({
  searchValue,
  onSearchChange,
  sources,
  allSourcesCount,
  selectedSources,
  summarySource,
  onToggleSource,
  onSelectAll,
  onClearSelection,
  onShowSummary,
  onDeleteSource,
  onRetrySource,
  onUploadSources,
  uploadProgress,
  uploadError,
  onCloseSummary,
  onClose,
  initialFocusRef,
  returnFocusRef,
}: {
  searchValue: string
  onSearchChange: (value: string) => void
  sources: SourceDocument[]
  allSourcesCount: number
  selectedSources: Set<string>
  summarySource?: SourceDocument
  onToggleSource: (sourceId: string) => void
  onSelectAll: () => void
  onClearSelection: () => void
  onShowSummary: (sourceId: string) => void
  onDeleteSource: (sourceId: string) => void
  onRetrySource: (sourceId: string) => void
  onUploadSources: (files: File[]) => void
  uploadProgress: number
  uploadError: string
  onCloseSummary: () => void
  onClose: () => void
  initialFocusRef: RefObject<HTMLInputElement | null>
  returnFocusRef: RefObject<HTMLButtonElement | null>
}) {
  const selectedCount = selectedSources.size
  const uploadInputRef = useRef<HTMLInputElement>(null)
  const handleUpload = (event: ChangeEvent<HTMLInputElement>) => {
    onUploadSources(Array.from(event.target.files ?? []))
    event.target.value = ""
  }

  return (
    <CenteredModal
      ariaLabelledBy="sources-modal-title"
      initialFocusRef={initialFocusRef}
      returnFocusRef={returnFocusRef}
      onRequestClose={onClose}
      maxWidth={720}
    >
      <div className="sources-header">
        <div>
          <h2 id="sources-modal-title">Sources</h2>
          <p>
            Select documents for the assistant to reference in your next
            message.
          </p>
        </div>
        <button
          type="button"
          aria-label="Close sources"
          onClick={onClose}
          className="icon-close-button"
        >
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
            <path
              d="M18 6 6 18M6 6l12 12"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
        </button>
      </div>

      {summarySource ? (
        <div className="source-summary-view">
          <button
            type="button"
            onClick={onCloseSummary}
            className="source-back-button"
          >
            <span aria-hidden="true">←</span> Back to sources
          </button>
          <div className="source-summary-file">
            <FileTypeIcon
              extension={getFileExtension(summarySource.filename)}
            />
            <div>
              <p className="source-summary-kicker">Quick summary</p>
              <h3>{summarySource.filename}</h3>
              <span>{formatSourceMetadata(summarySource)}</span>
            </div>
          </div>
          <ul className="source-summary-points">
            {(summarySource.summary ?? []).map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
          <p className="source-mock-note">
            Preview content is mocked for this visual prototype.
          </p>
        </div>
      ) : (
        <>
          <div className="sources-toolbar">
            <div className="sources-search-wrap">
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden="true"
              >
                <circle
                  cx="11"
                  cy="11"
                  r="7"
                  stroke="currentColor"
                  strokeWidth="2"
                />
                <path
                  d="m20 20-3-3"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
              <input
                ref={initialFocusRef}
                value={searchValue}
                onChange={(event) => onSearchChange(event.target.value)}
                placeholder="Search sources"
                aria-label="Search sources"
              />
            </div>
            <div className="sources-list-actions">
              <input
                ref={uploadInputRef}
                type="file"
                accept=".pdf,.docx,.txt,.md,.html,.csv,.tsv"
                multiple
                onChange={handleUpload}
                hidden
              />
              <button
                type="button"
                onClick={() => uploadInputRef.current?.click()}
                disabled={uploadProgress > 0 && uploadProgress < 100}
              >
                Upload
              </button>
              <button
                type="button"
                onClick={onSelectAll}
                disabled={sources.length === 0}
              >
                Select all
              </button>
              <button
                type="button"
                onClick={onClearSelection}
                disabled={selectedCount === 0}
              >
                Clear selection
              </button>
            </div>
          </div>

          {(uploadProgress > 0 || uploadError) && (
            <div className="source-upload-status" aria-live="polite">
              {uploadProgress > 0 && (
                <>
                  <span>
                    {uploadProgress < 100
                      ? `Uploading and processing… ${uploadProgress}%`
                      : "Upload complete"}
                  </span>
                  <progress value={uploadProgress} max={100} />
                </>
              )}
              {uploadError && (
                <p className="operation-error" role="alert">
                  {uploadError}
                </p>
              )}
            </div>
          )}

          <div
            className="sources-list"
            role="list"
            aria-label="Available sources"
          >
            {allSourcesCount === 0 ? (
              <div className="sources-empty-state">
                <div className="sources-empty-icon" aria-hidden="true">
                  ＋
                </div>
                <h3>No sources yet</h3>
                <p>Uploaded documents will appear here.</p>
                <button
                  type="button"
                  onClick={() => uploadInputRef.current?.click()}
                >
                  Upload document
                </button>
              </div>
            ) : sources.length === 0 ? (
              <div className="sources-empty-state">
                <h3>No matching sources</h3>
                <p>Try searching with a different filename or extension.</p>
              </div>
            ) : (
              sources.map((source) => {
                const selected = selectedSources.has(source.id)
                const extensionIndex = source.filename.lastIndexOf(".")
                const basename = source.filename.slice(0, extensionIndex)
                const extension = source.filename.slice(extensionIndex)

                return (
                  <div
                    key={source.id}
                    role="listitem"
                    className={`source-row${
                      selected ? " source-row-selected" : ""
                    }`}
                  >
                    <input
                      id={`source-${source.id}`}
                      type="checkbox"
                      checked={selected}
                      onChange={() => onToggleSource(source.id)}
                      aria-label={`Use ${source.filename} for next message`}
                      className="source-checkbox"
                    />
                    <FileTypeIcon
                      extension={getFileExtension(source.filename)}
                    />
                    <div className="source-details">
                      <label
                        htmlFor={`source-${source.id}`}
                        className="source-filename"
                        title={source.filename}
                        tabIndex={0}
                        aria-label={source.filename}
                      >
                        <span className="source-filename-base">{basename}</span>
                        <span className="source-filename-extension">
                          {extension}
                        </span>
                      </label>
                      <span className="source-metadata">
                        {formatSourceMetadata(source)}
                      </span>
                      <span
                        className={`source-status source-status-${source.status}`}
                      >
                        {source.status}
                        {source.error ? ` · ${source.error}` : ""}
                      </span>
                    </div>
                    <div className="source-row-actions">
                      <span className="source-selection-label">
                        {selected ? "Selected" : "Use for next message"}
                      </span>
                      <div className="source-row-buttons">
                        <button
                          type="button"
                          onClick={() => onShowSummary(source.id)}
                          aria-label={`Quick summary for ${source.filename}`}
                          className="quick-summary-button"
                        >
                          Quick summary
                        </button>
                        <button
                          type="button"
                          onClick={() => onDeleteSource(source.id)}
                          aria-label={`Delete ${source.filename}`}
                          className="delete-source-button"
                        >
                          Delete
                        </button>
                        {source.status === "failed" && (
                          <button
                            type="button"
                            onClick={() => onRetrySource(source.id)}
                            className="quick-summary-button"
                            aria-label={`Retry ${source.filename}`}
                          >
                            Retry
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>

          <div className="sources-footer">
            <div>
              <strong>
                {selectedCount} {selectedCount === 1 ? "source" : "sources"}{" "}
                selected
              </strong>
              <span>These sources will be referenced in your next message</span>
            </div>
            <button
              type="button"
              onClick={onClearSelection}
              disabled={selectedCount === 0}
            >
              Clear selection
            </button>
          </div>
        </>
      )}
    </CenteredModal>
  )
}

function FileTypeIcon({ extension }: { extension: string }) {
  return (
    <span
      className={`file-type-icon file-type-${extension.toLowerCase()}`}
      aria-hidden="true"
    >
      {extension}
    </span>
  )
}

function getFileExtension(filename: string): string {
  const extension = filename.split(".").pop()
  return extension && extension !== filename ? extension.toUpperCase() : "FILE"
}

function formatSourceMetadata(source: SourceDocument): string {
  const size = new Intl.NumberFormat(undefined, {
    style: "unit",
    unit: source.size >= 1_000_000 ? "megabyte" : "kilobyte",
    maximumFractionDigits: 1,
  }).format(
    source.size >= 1_000_000 ? source.size / 1_000_000 : source.size / 1_000,
  )

  const date = new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
  }).format(Date.parse(source.createdAt))

  return `${size} · Added ${date}`
}
