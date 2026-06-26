import { useState } from "react";

import { askRepository, indexLocalRepository } from "../api.js";
import { Button, Input, Textarea } from "./ui.jsx";

function RepoIndexer({ apiKey }) {
  const [localPath, setLocalPath] = useState("");
  const [indexResult, setIndexResult] = useState(null);
  const [indexError, setIndexError] = useState("");
  const [isIndexing, setIsIndexing] = useState(false);

  const [repoName, setRepoName] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [askError, setAskError] = useState("");
  const [isAsking, setIsAsking] = useState(false);

  async function handleIndex(event) {
    event.preventDefault();

    if (!apiKey) {
      setIndexError("Enter your API key before indexing a repository.");
      return;
    }

    if (!localPath.trim()) {
      setIndexError("Enter an absolute path on the backend machine.");
      return;
    }

    setIndexError("");
    setIndexResult(null);
    setIsIndexing(true);

    try {
      const result = await indexLocalRepository(apiKey, localPath.trim());
      setIndexResult(result);
      setRepoName(result.repo_name);
    } catch (requestError) {
      setIndexError(requestError.message);
    } finally {
      setIsIndexing(false);
    }
  }

  async function handleAsk(event) {
    event.preventDefault();

    if (!apiKey) {
      setAskError("Enter your API key before asking about a repository.");
      return;
    }

    if (!repoName.trim() || !question.trim()) {
      setAskError("Enter an indexed repository name and a question.");
      return;
    }

    setAskError("");
    setAnswer(null);
    setIsAsking(true);

    try {
      const result = await askRepository(
        apiKey,
        repoName.trim(),
        question.trim(),
      );
      setAnswer(result);
    } catch (requestError) {
      setAskError(requestError.message);
    } finally {
      setIsAsking(false);
    }
  }

  return (
    <section className="panel panel--large repo-panel">
      <div className="panel__heading">
        <div>
          <p className="section-kicker">Repository workspace</p>
          <h2>Index and ask</h2>
        </div>
        <span className="panel__tag">Keyword RAG</span>
      </div>

      <div className="repo-grid">
        <div className="repo-workflow">
          <div className="step-heading">
            <span>01</span>
            <div>
              <h3>Index a local repository</h3>
              <p>Build a JSON index from supported source files.</p>
            </div>
          </div>

          <form className="stacked-form" onSubmit={handleIndex}>
            <label className="field">
              <span className="field__label">Absolute path</span>
              <Input
                onChange={(event) => setLocalPath(event.target.value)}
                placeholder="/home/user/projects/my-repository"
                value={localPath}
              />
            </label>

            <p className="form-hint">
              For the fixture, run <code>realpath sample-code-repository</code>{" "}
              from the project root.
            </p>

            {indexError && (
              <div className="alert alert--error">{indexError}</div>
            )}

            {indexResult && (
              <div className="alert alert--success">
                <strong>{indexResult.repo_name}</strong> indexed successfully:
                {` ${indexResult.indexed_files} files and ${indexResult.indexed_chunks} chunks.`}
              </div>
            )}

            <Button
              className="secondary-button"
              disabled={isIndexing}
              type="submit"
              variant="secondary"
            >
              {isIndexing ? "Indexing..." : "Create index"}
            </Button>
          </form>
        </div>

        <div className="repo-workflow">
          <div className="step-heading">
            <span>02</span>
            <div>
              <h3>Ask the indexed codebase</h3>
              <p>Retrieve relevant chunks and send them to Ollama.</p>
            </div>
          </div>

          <form className="stacked-form" onSubmit={handleAsk}>
            <label className="field">
              <span className="field__label">Repository name</span>
              <Input
                onChange={(event) => setRepoName(event.target.value)}
                placeholder="sample-code-repository"
                value={repoName}
              />
            </label>

            <label className="field">
              <span className="field__label">Question</span>
              <Textarea
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Where are the add and multiply functions implemented?"
                rows="4"
                value={question}
              />
            </label>

            {askError && <div className="alert alert--error">{askError}</div>}

            {answer && (
              <div className="rag-answer" aria-live="polite">
                <p>{answer.answer}</p>
                <div>
                  <span className="field__label">Retrieved sources</span>
                  <ul className="source-list">
                    {answer.sources.length > 0 ? (
                      answer.sources.map((source) => (
                        <li key={source}>{source}</li>
                      ))
                    ) : (
                      <li>No matching source chunks</li>
                    )}
                  </ul>
                </div>
              </div>
            )}

            <Button
              className="secondary-button"
              disabled={isAsking}
              type="submit"
              variant="secondary"
            >
              {isAsking ? "Searching..." : "Ask repository"}
            </Button>
          </form>
        </div>
      </div>
    </section>
  );
}

export default RepoIndexer;
