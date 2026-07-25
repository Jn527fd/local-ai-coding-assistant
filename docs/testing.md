# Testing

The default suite is designed to run on a clean machine without Ollama,
downloaded models, GPU drivers, or host-specific data. Runtime limits such as
upload size, document chunk count, embedding batch size, `topK`, `candidateK`,
and prompt budgets are configured through `backend/app/config.py` so tests and
Docker runs can use conservative defaults.

The backend suite includes a repository hygiene guard that fails when a
tracked file matches `.gitignore`. This keeps local virtual environments,
dependency folders, generated indexes, build output, and machine-specific
artifacts out of future commits.

## Local Setup

Install backend and production frontend test dependencies from the committed app-specific
dependency files:

```bash
python -m pip install -r requirements-dev.txt
pnpm --dir proposedFrontend install --frozen-lockfile
```

Run the backend tests:

```bash
make test-backend
```

Run frontend lint, unit tests, and a production build:

```bash
make test-frontend
```

Run both:

```bash
make test
```

## Frontend Checks

The production frontend lives in `proposedFrontend/`. `make test-frontend`
runs linting, TypeScript, Vitest, and a production build against that app. The
archived legacy frontend can still be checked explicitly with
`make test-legacy-frontend`.

## Continuous Integration

GitHub Actions runs the default hermetic checks on pushes to `main`,
`phase-*` branches, and pull requests:

- Backend dependency install from `requirements-dev.txt`
- Backend `python -m pytest`
- Frontend `pnpm install --frozen-lockfile`
- Frontend lint
- Frontend TypeScript
- Frontend Vitest suite
- Frontend production build

The CI workflow sets `RUN_OLLAMA_TESTS=0`, so live Ollama tests remain skipped
unless a developer runs them explicitly outside the default workflow.

## Docker Tests

The test Compose file uses separate test images and does not mount local app
data:

```bash
make test-backend-docker
make test-frontend-docker
make test-docker
```

Use smoke checks when you want a faster confidence pass:

```bash
make smoke
make smoke-docker
```

The Dockerized backend/frontend suite is also available as a manual GitHub
Actions workflow named `Docker Verification`. It is not part of the default CI
path because Docker image builds are slower than the normal hermetic test
jobs.

## Ollama Isolation

Backend tests should mock Ollama through dependency injection or HTTPX mock
transports. Frontend tests should use MSW handlers. Browser tests can start the
deterministic fake server at `tests/fakes/fake_ollama.py`, which implements the
Ollama endpoints used by this application:

- `GET /api/tags`
- `POST /api/generate`
- `POST /api/embed`
- `POST /api/embeddings`

The fake server returns deterministic chat text, deterministic embeddings, and
numeric reranker scores without logging prompt bodies.

## Optional Live Ollama Tests

Tests marked `ollama` are skipped unless explicitly enabled:

```bash
RUN_OLLAMA_TESTS=1 make test-ollama
```

To require a particular local model, set `OLLAMA_TEST_MODEL`. The test will
skip cleanly if the daemon is reachable but the model is missing:

```bash
OLLAMA_TEST_MODEL=qwen3:4b RUN_OLLAMA_TESTS=1 make test-ollama
```

## CPU-Friendly Ollama Smoke Profile

The live smoke profile is an opt-in integration check for CPU-only laptops. It
uses tiny models to validate wiring, not response quality, speed, or production
model behavior. Default local and Docker test commands do not run this profile.

Set up the smoke models:

```bash
make setup-ollama-smoke
```

The setup command checks whether the `ollama` CLI is installed, verifies the
daemon at `OLLAMA_BASE_URL` or `http://127.0.0.1:11434`, and pulls only small
CPU-friendly models:

- `smollm2:135m` for chat/generation
- `all-minilm` for embeddings

It does not pull large 7B or 8B models. The optional reranker model is pulled
only when explicitly requested:

```bash
PULL_RERANKER=1 make setup-ollama-smoke
```

The live smoke environment variables are:

```bash
OLLAMA_TEST_LLM=smollm2:135m
OLLAMA_TEST_EMBEDDER=all-minilm
OLLAMA_TEST_RERANKER=qllama/bge-reranker-v2-m3:q4_k_m
OLLAMA_TEST_VISION=llava:latest
```

Run the live smoke suite:

```bash
RUN_OLLAMA_TESTS=1 make test-ollama-smoke
```

Run the optional reranker smoke after pulling the reranker:

```bash
RUN_OLLAMA_TESTS=1 RUN_RERANKER_TESTS=1 make test-ollama-smoke
```

Run the optional vision smoke only after you have pulled a local vision model:

```bash
RUN_OLLAMA_TESTS=1 RUN_VISION_TESTS=1 OLLAMA_TEST_VISION=llava:latest make test-ollama-smoke
```

The smoke suite checks that Ollama is reachable, `/api/tags` returns models,
chat generation works, embeddings work, document upload/process/index/search
works with live embeddings, and RAG chat retrieves indexed chunks before
answering with the tiny LLM. Optional reranker and vision tests are skipped
unless explicitly enabled. If Ollama is missing, not running, or required
models are not pulled, tests skip with a clear message.

CPU-only execution is supported but can be slower. Production-quality model
testing should happen on the machine that has the real pulled models and GPU.

## Retrieval Evaluation

The deterministic retrieval evaluation harness uses fake embeddings and a
small non-sensitive fixture corpus under `tests/fixtures/retrieval_eval/`.
It is a wiring and regression baseline, not a model quality benchmark.

Run the retrieval evaluation tests with:

```bash
python -m pytest tests/test_retrieval_eval.py
```

The harness measures:

- recall against expected chunk IDs
- best rank for expected chunks
- source metadata accuracy
- expected warning behavior
- source numbering and response payload shape

Live embedding/model evaluation remains opt-in only. Do not add live model
quality checks to the default suite; gate them behind explicit environment
variables in the same style as the Ollama smoke tests.

## Frontend E2E

Playwright is not part of the default frontend test target. Run it
separately when browser coverage is needed:

```bash
cd proposedFrontend
pnpm test:e2e
```

The Playwright config starts the fake Ollama server, the FastAPI backend, and
the Vite frontend.

## Markers

Pytest markers are registered in `pytest.ini`:

- `unit`
- `integration`
- `slow`
- `ollama`
- `ollama_smoke`
- `documents`
- `vector`
- `rag`

Use markers to keep future tests explicit about their runtime requirements.
