import { useState, type FormEvent } from "react"
import { Link } from "react-router-dom"
import { appServices, type RepositoryService } from "../../services"
import { normalizeError } from "../../services/errors"
import type {
  RepositoryAskResult,
  RepositoryIndexResult,
  RepositoryVectorIndexResult,
  RepositoryVectorSearchResult,
} from "../../services/contracts"

export function RepositoryPage({
  repositoryService = appServices.repositories,
}: {
  repositoryService?: RepositoryService
}) {
  const [path, setPath] = useState("")
  const [repoName, setRepoName] = useState("")
  const [conversationId, setConversationId] = useState("default")
  const [question, setQuestion] = useState("")
  const [vectorQuery, setVectorQuery] = useState("")
  const [indexing, setIndexing] = useState(false)
  const [vectorIndexing, setVectorIndexing] = useState(false)
  const [asking, setAsking] = useState(false)
  const [searching, setSearching] = useState(false)
  const [indexResult, setIndexResult] = useState<RepositoryIndexResult | null>(
    null,
  )
  const [vectorIndexResult, setVectorIndexResult] =
    useState<RepositoryVectorIndexResult | null>(null)
  const [askResult, setAskResult] = useState<RepositoryAskResult | null>(null)
  const [searchResult, setSearchResult] =
    useState<RepositoryVectorSearchResult | null>(null)
  const [error, setError] = useState("")

  const handleIndex = async (event: FormEvent) => {
    event.preventDefault()
    if (!path.trim()) {
      setError("Enter an absolute repository path on the backend machine.")
      return
    }
    setError("")
    setIndexing(true)
    try {
      const result = await repositoryService.indexLocal(path.trim())
      setIndexResult(result)
      setRepoName(result.repoName)
    } catch (caught) {
      setError(normalizeError(caught).message)
    } finally {
      setIndexing(false)
    }
  }

  const handleVectorIndex = async () => {
    if (!path.trim() || !conversationId.trim()) {
      setError(
        "Enter a repository path and conversation id before vector indexing.",
      )
      return
    }
    setError("")
    setVectorIndexing(true)
    try {
      const result = await repositoryService.indexVector({
        path: path.trim(),
        conversationId: conversationId.trim(),
      })
      setVectorIndexResult(result)
      setRepoName(result.repoName)
    } catch (caught) {
      setError(normalizeError(caught).message)
    } finally {
      setVectorIndexing(false)
    }
  }

  const handleAsk = async (event: FormEvent) => {
    event.preventDefault()
    if (!repoName.trim() || !question.trim()) {
      setError("Enter an indexed repository name and a question.")
      return
    }
    setError("")
    setAsking(true)
    try {
      setAskResult(
        await repositoryService.ask({
          repoName: repoName.trim(),
          question: question.trim(),
        }),
      )
    } catch (caught) {
      setError(normalizeError(caught).message)
    } finally {
      setAsking(false)
    }
  }

  const handleVectorSearch = async (event: FormEvent) => {
    event.preventDefault()
    if (!conversationId.trim() || !vectorQuery.trim()) {
      setError("Enter a conversation id and vector search query.")
      return
    }
    setError("")
    setSearching(true)
    try {
      setSearchResult(
        await repositoryService.searchVector({
          conversationId: conversationId.trim(),
          repoName: repoName.trim() || undefined,
          query: vectorQuery.trim(),
          topK: 5,
        }),
      )
    } catch (caught) {
      setError(normalizeError(caught).message)
    } finally {
      setSearching(false)
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

      <main id="repository-main" className="profile-main" tabIndex={-1}>
        <div className="profile-page-heading">
          <span className="profile-page-kicker">Repository intelligence</span>
          <h1>Repositories</h1>
          <p>
            Index local code, ask keyword-RAG questions, or search opt-in
            repository vectors.
          </p>
        </div>

        {error && (
          <section className="profile-card profile-load-error" role="alert">
            <h2>Repository request failed</h2>
            <p>{error}</p>
          </section>
        )}

        <section className="profile-card repository-grid">
          <form onSubmit={handleIndex} className="repository-panel">
            <h2>Index local repository</h2>
            <label className="profile-field">
              <span>Absolute path</span>
              <input
                value={path}
                onChange={(event) => setPath(event.target.value)}
                placeholder="C:\\Users\\you\\projects\\repo"
              />
            </label>
            <button className="profile-primary-button" disabled={indexing}>
              {indexing ? "Indexing..." : "Create keyword index"}
            </button>
            <button
              type="button"
              className="profile-secondary-button"
              disabled={vectorIndexing}
              onClick={() => void handleVectorIndex()}
            >
              {vectorIndexing ? "Embedding..." : "Create vector index"}
            </button>
            {indexResult && <RepositoryIndexSummary result={indexResult} />}
            {vectorIndexResult && (
              <RepositoryIndexSummary result={vectorIndexResult} vector />
            )}
          </form>

          <form onSubmit={handleAsk} className="repository-panel">
            <h2>Ask indexed repository</h2>
            <RepositorySharedFields
              repoName={repoName}
              conversationId={conversationId}
              onRepoName={setRepoName}
              onConversationId={setConversationId}
            />
            <label className="profile-field">
              <span>Question</span>
              <textarea
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                rows={4}
              />
            </label>
            <button className="profile-primary-button" disabled={asking}>
              {asking ? "Asking..." : "Ask repository"}
            </button>
            {askResult && <RepositoryAskSummary result={askResult} />}
          </form>

          <form onSubmit={handleVectorSearch} className="repository-panel">
            <h2>Search repository vectors</h2>
            <RepositorySharedFields
              repoName={repoName}
              conversationId={conversationId}
              onRepoName={setRepoName}
              onConversationId={setConversationId}
            />
            <label className="profile-field">
              <span>Vector query</span>
              <textarea
                value={vectorQuery}
                onChange={(event) => setVectorQuery(event.target.value)}
                rows={4}
              />
            </label>
            <button className="profile-primary-button" disabled={searching}>
              {searching ? "Searching..." : "Search vectors"}
            </button>
            {searchResult && (
              <RepositoryVectorSearchSummary result={searchResult} />
            )}
          </form>
        </section>
      </main>
    </div>
  )
}

function RepositorySharedFields({
  repoName,
  conversationId,
  onRepoName,
  onConversationId,
}: {
  repoName: string
  conversationId: string
  onRepoName: (value: string) => void
  onConversationId: (value: string) => void
}) {
  return (
    <>
      <label className="profile-field">
        <span>Repository name</span>
        <input
          value={repoName}
          onChange={(event) => onRepoName(event.target.value)}
        />
      </label>
      <label className="profile-field">
        <span>Conversation id</span>
        <input
          value={conversationId}
          onChange={(event) => onConversationId(event.target.value)}
        />
      </label>
    </>
  )
}

function RepositoryIndexSummary({
  result,
  vector = false,
}: {
  result: RepositoryIndexResult | RepositoryVectorIndexResult
  vector?: boolean
}) {
  const vectorResult = vector ? result as RepositoryVectorIndexResult : null
  return (
    <div className="repository-result" role="status">
      <strong>{result.repoName}</strong>
      <span>
        {result.indexedFiles} files, {result.indexedChunks} chunks
      </span>
      {vectorResult && (
        <span>
          {vectorResult.embeddedChunks} embedded chunks in{" "}
          {vectorResult.collectionId}
        </span>
      )}
      <RepositoryWarnings
        warnings={[
          ...(result.warnings ?? []),
          ...(result.freshness?.warnings ?? []),
        ]}
      />
    </div>
  )
}

function RepositoryAskSummary({ result }: { result: RepositoryAskResult }) {
  return (
    <div className="repository-result">
      <p>{result.answer}</p>
      <RepositoryWarnings
        warnings={[...result.warnings, ...(result.freshness?.warnings ?? [])]}
      />
      <ul>
        {result.sources.map((source) => (
          <li key={source}>{source}</li>
        ))}
      </ul>
    </div>
  )
}

function RepositoryVectorSearchSummary({
  result,
}: {
  result: RepositoryVectorSearchResult
}) {
  return (
    <div className="repository-result">
      <RepositoryWarnings warnings={result.warnings} />
      <ol>
        {result.results.map((item, index) => (
          <li key={`${item.filePath}-${index}`}>
            <strong>
              {item.filePath ?? item.repoName ?? "Repository chunk"}
            </strong>
            <span>
              {item.symbolName
                ? ` ${item.symbolKind ?? "symbol"} ${item.symbolName}`
                : ""}
            </span>
            <span> Score {item.score.toFixed(3)}</span>
            <p>{item.text}</p>
          </li>
        ))}
      </ol>
    </div>
  )
}

function RepositoryWarnings({ warnings }: { warnings: string[] }) {
  const unique = [...new Set(warnings.filter(Boolean))]
  if (unique.length === 0) return null
  return (
    <ul className="repository-warnings" aria-label="Repository warnings">
      {unique.map((warning) => (
        <li key={warning}>{warning}</li>
      ))}
    </ul>
  )
}
