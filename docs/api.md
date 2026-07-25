# API Reference

## Base URL

The default backend is `http://localhost:8000`. Interactive OpenAPI
documentation is available at `/docs`.

## Authentication Layers

The app uses two local authentication mechanisms:

1. **Login session cookie:** `/auth/login` verifies
   `data/config/credentials.json` and sets an HttpOnly cookie. Account,
   model, component-discovery, and optional conversation-persistence endpoints
   require this cookie. Unsafe session-cookie requests also require the CSRF
   token from the readable `local_ai_csrf` cookie in the `X-CSRF-Token` header.
2. **Bearer API key:** `/chat`, `/documents/*`, and `/repos/*` require
   `Authorization: Bearer <API_KEY>`. The active key comes from the ignored
   local app-settings file, with the `API_KEY` environment variable as a
   fallback.

`GET /` and `GET /health` are public.

## Endpoint Summary

| Method | Path | Authentication | Purpose |
| --- | --- | --- | --- |
| `GET` | `/` | None | Application metadata |
| `GET` | `/health` | None | Backend process health |
| `POST` | `/auth/login` | None | Create local browser session |
| `GET` | `/auth/me` | Session | Return signed-in user |
| `POST` | `/auth/logout` | Session | Revoke current session |
| `GET` | `/account/status` | Session | Check API-key state |
| `PUT` | `/account/api-key` | Session | Persist a new API key |
| `GET` | `/models/status` | Session | Legacy model status and Ollama connectivity |
| `POST` | `/models/switch` | Session | Legacy active-model fallback switch |
| `GET` | `/components/capabilities` | Session | Categorized local models, tools, and static component options |
| `GET` | `/conversations` | Session | List optional backend-persisted conversations for the signed-in local user |
| `POST` | `/conversations` | Session | Create or replace one persisted conversation |
| `GET` | `/conversations/{conversation_id}` | Session | Read one persisted conversation |
| `PUT` | `/conversations/{conversation_id}` | Session | Update one persisted conversation |
| `DELETE` | `/conversations/{conversation_id}` | Session | Delete one persisted conversation |
| `POST` | `/conversations/import` | Session | Import browser conversations into backend persistence |
| `GET` | `/conversations/export/all` | Session | Export backend-persisted conversations |
| `POST` | `/chat` | Bearer key | Generate a complete chat response with optional document RAG, reranking, compression, and vision |
| `POST` | `/chat/stream` | Bearer key | Stream chat progress, tokens, metadata, and completion events |
| `POST` | `/documents/upload` | Bearer key | Stage a document for one conversation |
| `POST` | `/documents/{document_id}/process` | Bearer key | Extract text and chunk a staged document |
| `POST` | `/documents/{document_id}/process/jobs` | Bearer key | Start a local background processing job |
| `POST` | `/documents/{document_id}/index` | Bearer key | Embed and index one processed document |
| `POST` | `/documents/{document_id}/index/jobs` | Bearer key | Start a local background indexing job |
| `POST` | `/documents/search` | Bearer key | Search indexed document chunks without chat |
| `GET` | `/documents` | Bearer key | List documents for one conversation |
| `GET` | `/documents/indexes` | Bearer key | List vector collections for one conversation |
| `DELETE` | `/documents/indexes/{collection_id}` | Bearer key | Delete one vector collection |
| `GET` | `/documents/{document_id}` | Bearer key | Get document metadata |
| `GET` | `/documents/{document_id}/chunks` | Bearer key | Get processed document chunks |
| `GET` | `/vectorstores/health` | Bearer key | Inspect vector backend availability and fallback state |
| `GET` | `/vectorstores/collections/export` | Bearer key | Export one vector collection as a portable JSON payload |
| `POST` | `/vectorstores/collections/import` | Bearer key | Import a portable vector collection payload |
| `POST` | `/vectorstores/collections/migrate` | Bearer key | Copy a collection from one available vector backend to another |
| `GET` | `/diagnostics/status` | Bearer key | Return redacted runtime/model/document/retrieval/job diagnostics |
| `GET` | `/diagnostics/support-bundle` | Bearer key | Export a redacted metadata-only support bundle |
| `GET` | `/jobs` | Bearer key | List recent local background jobs |
| `GET` | `/jobs/{job_id}` | Bearer key | Read local job status, progress, result, or error |
| `POST` | `/jobs/{job_id}/cancel` | Bearer key | Request conservative cancellation for a local job |
| `POST` | `/repos/index-local` | Bearer key | Index a local repository with legacy keyword RAG |
| `POST` | `/repos/ask` | Bearer key | Ask a grounded question against a repository index |
| `POST` | `/repos/index-local/vector` | Bearer key | Opt into embedding repository chunks |
| `POST` | `/repos/search-vector` | Bearer key | Search opt-in repository vector collections |

## Public Endpoints

```bash
curl http://localhost:8000/
curl http://localhost:8000/health
```

`GET /health` returns:

```json
{"status":"ok"}
```

It confirms FastAPI is running; it does not verify Ollama.

## Login Session

Use a cookie jar for command-line testing:

```bash
curl -c session.cookies -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"YOUR_USERNAME","password":"YOUR_PASSWORD"}'
```

Successful response:

```json
{"username":"YOUR_USERNAME"}
```

Check the session:

```bash
curl -b session.cookies http://localhost:8000/auth/me
```

For unsafe session-cookie requests such as logout or API-key updates, send the
CSRF token from the cookie jar:

```bash
CSRF_TOKEN=$(grep local_ai_csrf session.cookies | awk '{print $7}')
curl -b session.cookies -X POST http://localhost:8000/auth/logout \
  -H "X-CSRF-Token: $CSRF_TOKEN"
```

Invalid credentials return `401`. A missing or malformed credentials file
returns `503` with a local setup message. Repeated invalid attempts return
`429` until the local lockout window expires.

## Account API Key

Save a local key. Short keys are accepted for testing, but a longer private
key is recommended for normal use:

```bash
curl -b session.cookies -X PUT http://localhost:8000/account/api-key \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF_TOKEN" \
  -d '{"api_key":"your-private-api-key"}'
```

For frontend compatibility, this endpoint also accepts camelCase
`{"apiKey":"..."}`. Responses preserve the existing snake_case shape.

The response never includes the secret:

```json
{
  "username": "YOUR_USERNAME",
  "api_key_configured": true,
  "api_key_active": true
}
```

Check whether a candidate key matches the active key:

```bash
curl -b session.cookies http://localhost:8000/account/status \
  -H "Authorization: Bearer your-private-api-key"
```

The backend persists the active key in
`data/config/app-settings.json`. The React frontend also stores the user's
entered copy in browser local storage.

## Model Status and Component Capabilities

`/models/status` is preserved for backward compatibility and current runtime
health display:

```bash
curl -b session.cookies http://localhost:8000/models/status
```

It returns `active_model`, `supported_models`, `installed_models`,
`ollama_connected`, `switching`, `phase`, `progress`, `message`, `error`, and
`warning`.

The current per-chat settings UI is backed by component discovery:

```bash
curl -b session.cookies http://localhost:8000/components/capabilities
```

The response contains these categories:

```json
{
  "llmModels": [],
  "embedderModels": [],
  "rerankerModels": [],
  "visionModels": [],
  "ocrEngines": [],
  "pdfParsers": [],
  "chunkers": [],
  "vectorDatabases": [],
  "ragPipelines": [],
  "contextCompressors": [],
  "unknownOllamaModels": []
}
```

Every entry includes `id`, `label`, `type`, `available`, `source`,
`implementationStatus`, `implemented`, and an `execution` object. The
execution object includes `status`, `implemented`, `mode`, and `description`.
Known statuses are:

- `implemented`: the selected capability has a direct execution path.
- `fallback`: the setting is accepted, but execution currently falls back to a
  simpler implemented path.
- `placeholder`: the setting is exposed for future compatibility only.
- `discovery-only`: the local model or tool is detected, but this app cannot
  execute that capability yet.
- `unavailable`: required package or binary checks did not pass in the backend
  runtime.

Ollama model entries also include `name`, `size`, `sizeBytes`, `modifiedAt`,
and `details` when available. Local tool entries include package/binary
`checks`. Static options may describe future-compatible settings; use
`implementationStatus` and `execution.mode` before treating a static option as
fully executable.

## Conversation Settings

Chat and document endpoints accept the same optional `conversationSettings`
shape:

```json
{
  "llmModel": "llama3.2:3b",
  "embedderModel": "nomic-embed-text:latest",
  "ocrEngine": "none",
  "pdfParser": "pymupdf",
  "chunker": "recursive",
  "vectorDatabase": "chroma",
  "ragPipeline": "basic",
  "reranker": "none",
  "contextCompressor": "none",
  "visionModel": "none"
}
```

Extra fields are ignored inside `conversationSettings`. Invalid or unavailable
components are resolved by the backend and usually produce warnings or clear
validation errors depending on the operation.

## Optional Conversation Persistence

Browser localStorage remains the default conversation store. When a user opts
in from Settings, the frontend imports browser chats into backend persistence
with `POST /conversations/import` and then keeps the backend JSON store updated.

Conversation persistence endpoints require the login session cookie and are
scoped to the signed-in local username. They do not use the Bearer API key and
do not provide cloud sync.

Persisted conversations are stored under `data/conversations/` as local JSON.
Each record can include:

- `id`
- `title`
- `messages`
- `settings`
- `metadata`
- `attachmentReferences`
- `createdAt`
- `updatedAt`

`DELETE /conversations/{conversation_id}` removes the persisted record so it is
not returned by future list/read calls. Browser-local fallback data is managed
by the frontend.

## Chat

Chat uses the selected per-conversation `llmModel` when supplied. The legacy
global active model remains a fallback.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId":"chat-1",
    "message":"Explain dependency injection briefly.",
    "conversationSettings":{
      "llmModel":"llama3.2:3b",
      "ragPipeline":"basic",
      "reranker":"none",
      "contextCompressor":"none"
    },
    "ragOptions":{
      "enabled":false,
      "topK":5,
      "candidateK":20,
      "documentIds":[],
      "includeSources":true
    },
    "history":[
      {"role":"user","content":"What is FastAPI?"},
      {"role":"assistant","content":"FastAPI is a Python web framework."}
    ],
    "images":[
      {
        "name":"diagram.png",
        "mimeType":"image/png",
        "data":"BASE64_IMAGE_BYTES"
      }
    ]
  }'
```

`images` is optional. When supplied, the backend requires
`conversationSettings.visionModel` to resolve to an available local Ollama
vision model. Supported MIME types are `image/png`, `image/jpeg`, and
`image/webp`; each image is validated before the request is sent to Ollama.

`POST /chat/stream` accepts the same request body and returns
`text/event-stream`. Events are:

- `progress`: runtime stage updates such as `generating`.
- `metadata`: resolved model, RAG/rerank/compression/vision metadata, and
  sources.
- `token`: one generated text chunk.
- `done`: final answer plus the same metadata shape as `/chat`.
- `error`: recoverable streaming generation failure with `status` and
  `message`.

Response:

```json
{
  "model": "llama3.2:3b",
  "answer": "Generated text from the local model.",
  "ragUsed": false,
  "ragWarnings": [],
  "rerankingUsed": false,
  "rerankerModel": null,
  "rerankWarnings": [],
  "compressionUsed": false,
  "compressorMode": "none",
  "compressionWarnings": [],
  "compressionStats": {
    "originalCharEstimate": 0,
    "compressedCharEstimate": 0,
    "originalTokenEstimate": 0,
    "compressedTokenEstimate": 0,
    "messagesTrimmed": 0,
    "contextTrimmed": 0,
    "summaryGenerated": false
  },
  "visionUsed": false,
  "visionModel": null,
  "visionWarnings": [],
  "sources": []
}
```

`history` accepts at most 30 user/assistant messages. The backend does not
persist chat history. It builds a bounded prompt using
`CHAT_CONTEXT_MAX_CHARS`, optional retrieved document context, optional
reranking, and optional compression.

Common errors:

| Status | Meaning |
| --- | --- |
| `400` | Invalid request, invalid selected component, or missing required embedder for RAG |
| `401` | Bearer key is missing or invalid |
| `409` | Legacy model mismatch or switch in progress |
| `422` | Request validation failed |
| `502` | Ollama returned an invalid/error response |
| `503` | API key is unconfigured or Ollama is unavailable |
| `504` | Ollama timed out |

## Documents

Document endpoints are scoped by `conversationId`. Supported uploads are
`.txt`, `.md`, `.pdf`, `.docx`, `.html`, `.htm`, `.csv`, and `.tsv`. Uploads
are sniffed before storage so malformed files and obvious extension/content
mismatches return clear `400` errors. PDFs require an available parser such as
PyMuPDF or pdfplumber inside the backend runtime. DOCX, HTML, CSV, and TSV
extraction uses Python standard-library parsers. When `ocrEngine` is set to
`ocrmypdf` and the selected parser extracts very little text, processing
attempts an OCRmyPDF fallback if the `ocrmypdf` binary is available.

Upload uses multipart form data. `conversationSettings` is a JSON string:

```bash
curl -X POST http://localhost:8000/documents/upload \
  -H "Authorization: Bearer $API_KEY" \
  -F "conversationId=chat-1" \
  -F 'conversationSettings={"pdfParser":"pymupdf","ocrEngine":"none","chunker":"recursive"}' \
  -F "file=@notes.pdf"
```

Process the uploaded document:

```bash
curl -X POST http://localhost:8000/documents/DOCUMENT_ID/process \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId":"chat-1",
    "conversationSettings":{
      "pdfParser":"pymupdf",
      "ocrEngine":"none",
      "chunker":"recursive"
    }
  }'
```

Index the processed chunks with a valid available embedder:

```bash
curl -X POST http://localhost:8000/documents/DOCUMENT_ID/index \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId":"chat-1",
    "conversationSettings":{
      "embedderModel":"nomic-embed-text:latest",
      "vectorDatabase":"chroma"
    }
  }'
```

By default, vectors are persisted in the local JSON store.
`VECTOR_STORE_BACKEND=chroma` enables the optional Chroma adapter only when the
`chromadb` Python package is installed; otherwise JSON remains the fallback.
Qdrant and LanceDB are reported as deferred adapters and do not require
external services for default tests or Docker runs.

Document artifacts are checked before processing and indexing. Missing
documents return `404`, invalid requests return `400`, unreadable artifacts
return safe failed metadata or warnings, and malformed chunk artifacts are not
indexed. Empty extracted text marks processing as failed instead of producing a
processed document with zero chunks.
Document metadata includes file-type sniffing fields, extraction diagnostics,
and duplicate-upload markers when the same file content already exists in a
conversation.

The synchronous process and index endpoints remain available. For UI progress,
start the job variants and poll `/jobs/{job_id}`:

```bash
curl -X POST http://localhost:8000/documents/DOCUMENT_ID/process/jobs \
  -H "Authorization: Bearer your-private-api-key" \
  -H "Content-Type: application/json" \
  -d '{"conversationId":"chat-1","conversationSettings":{}}'

curl http://localhost:8000/jobs/JOB_ID \
  -H "Authorization: Bearer your-private-api-key"
```

Job states are `queued`, `running`, `succeeded`, `failed`,
`cancel_requested`, and `cancelled`. Cancellation is best-effort and only takes
effect at safe checkpoints; it does not interrupt an active Ollama request
mid-call.

Search indexed chunks:

```bash
curl -X POST http://localhost:8000/documents/search \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId":"chat-1",
    "query":"What does this document say about setup?",
    "conversationSettings":{
      "embedderModel":"nomic-embed-text:latest",
      "vectorDatabase":"chroma"
    },
    "topK":5
  }'
```

List documents, indexes, and chunks:

```bash
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/documents?conversationId=chat-1"

curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/documents/indexes?conversationId=chat-1"

curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/documents/DOCUMENT_ID/chunks?conversationId=chat-1"
```

Delete one index:

```bash
curl -X DELETE -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/documents/indexes/COLLECTION_ID?conversationId=chat-1"
```

Inspect vector backends:

```bash
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/vectorstores/health"
```

Export, import, or migrate a collection:

```bash
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:8000/vectorstores/collections/export?conversationId=chat-1&collectionId=COLLECTION_ID&backend=json"

curl -X POST http://localhost:8000/vectorstores/collections/import \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"backend":"json","payload":{}}'

curl -X POST http://localhost:8000/vectorstores/collections/migrate \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId":"chat-1",
    "collectionId":"COLLECTION_ID",
    "sourceBackend":"json",
    "targetBackend":"chroma"
  }'
```

The portable export format is intended for local backup and adapter migration.
If a requested optional backend is unavailable, migration/import falls back to
JSON and reports `fallbackUsed: true`.

## Diagnostics

Diagnostics endpoints are Bearer-key protected and return metadata only. They
are intended for local troubleshooting, not public telemetry.

```bash
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/diagnostics/status

curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/diagnostics/support-bundle
```

`/diagnostics/status` summarizes runtime configuration, model/Ollama status,
document counts, retrieval/vector backend status, and recent job states.
`/diagnostics/support-bundle` wraps that status with redaction metadata and is
safe by default for sharing with maintainers after review.

Diagnostics and support bundles exclude secrets, bearer values, cookies,
session identifiers, CSRF values, prompts, chat text, document/OCR contents,
and private file paths. Failure messages are redacted recursively before being
returned.

## RAG, Reranking, and Compression

Document RAG is attempted when the resolved RAG pipeline is one of `hybrid`,
`reranked`, `graph`, or `agentic`, or when request `ragOptions.enabled` asks
for retrieval. Current retrieval uses local embeddings and the active vector
store selected by `VECTOR_STORE_BACKEND`, with JSON as the safe fallback.

Reranking is attempted when the selected reranker is valid and not `none`, or
when `ragPipeline` is `reranked` with a valid reranker. The Ollama reranker
adapter asks the selected local model for a numeric relevance score per
candidate. Failures fall back to vector-ranked chunks and produce
`rerankWarnings`.

Compression modes:

- `none`: no compression.
- `token`: deterministic trimming.
- `summarizer`: LLM-generated summary of older history.
- `semantic`: currently falls back to token compression with a warning.
- `memory`: currently falls back to summarizer or token compression with a
  warning.

Returned RAG `sources` are ordered exactly as they were injected into the final
prompt after vector ranking, optional reranking, and optional compression.
`sourceNumber` and `finalRank` are one-based positions in that final prompt
context. `vectorScore` is the original vector similarity score, `rerankScore`
is present only when reranking succeeded, and `score` is the final score used
for the displayed ordering. `textPreview` is normalized and bounded for UI
display, and `collectionId` identifies the vector collection that produced the
source when available. Component discovery reports vector backend adapter
health and JSON fallback metadata.

## Repository Indexing

Legacy repository keyword RAG remains available:

```bash
SAMPLE_REPO_PATH="$(realpath sample-code-repository)"

curl -X POST http://localhost:8000/repos/index-local \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"path\":\"$SAMPLE_REPO_PATH\"}"
```

Docker uses `/repositories/...` paths. The response contains `repo_name`,
`indexed_files`, `indexed_chunks`, and freshness metadata. Index files are
stored beneath `DATA_DIRECTORY/indexes`.

Repository paths must be inside trusted roots. By default, the backend allows
the project root, the configured data directory, and `/repositories`. Set
`REPOSITORY_ALLOWED_ROOTS` to a comma-separated list to allow other local
folders.

Supported extensions are `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.md`, `.json`,
`.yaml`, `.yml`, `.html`, and `.css`. `.git`, `node_modules`, `.venv`,
`__pycache__`, `dist`, and `build` directories are ignored.

The repository indexer uses lightweight language-aware parsing for supported
extensions. Chunks can include `language`, `symbol_name`, `symbol_kind`,
`chunk_type`, and parser metadata while preserving the older `content`,
`file_path`, `start_line`, and `end_line` fields. Parser failures fall back to
line-based chunks.

## Repository Questions

```bash
curl -X POST http://localhost:8000/repos/ask \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_name": "sample-code-repository",
    "question": "Where are the add and multiply functions implemented?"
  }'
```

For frontend compatibility, this endpoint also accepts camelCase
`{"repoName":"sample-code-repository","question":"..."}`. Responses preserve
the existing `repo_name` and source metadata conventions used by legacy clients.

Response:

```json
{
  "answer": "The functions are implemented in sample_app/calculator.py.",
  "sources": ["app.py", "sample_app/calculator.py"],
  "warnings": [],
  "freshness": {
    "fresh": true,
    "warnings": []
  }
}
```

## Repository Vector Search

Repository vector indexing is opt-in and separate from document vector
collections:

```bash
curl -X POST http://localhost:8000/repos/index-local/vector \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/repositories/sample-code-repository",
    "conversationId": "local-chat-1",
    "conversationSettings": {
      "embedderModel": "all-minilm"
    }
  }'
```

Search indexed repository vectors without changing legacy keyword repository
RAG:

```bash
curl -X POST http://localhost:8000/repos/search-vector \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId": "local-chat-1",
    "query": "Where is authentication handled?",
    "topK": 5,
    "conversationSettings": {
      "embedderModel": "all-minilm"
    }
  }'
```

Repository vector results include `repoName`, `filePath`, line range metadata,
`language`, `symbolName`, `symbolKind`, vector score, and stale-index warnings
when the source files have changed.
Document search and document RAG ignore repository vector collections unless a
future phase explicitly unifies those prompts.

## Security Notes

- Do not expose these endpoints directly to the public internet.
- Use HTTPS before sending cookies or Bearer keys across an untrusted network.
- Review `SECURITY.md` and `docs/deployment-hardening.md` before remote
  deployment.
- The session cookie is HttpOnly and SameSite=Lax, but local HTTP is not
  encrypted.
- An authenticated Bearer caller can upload documents and index paths readable
  by the backend.
- Component discovery may show local packages or binaries available in the
  backend runtime.
- Model files are never downloaded or deleted by the application.
