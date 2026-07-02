# API Reference

## Base URL

The default backend is `http://localhost:8000`. Interactive OpenAPI
documentation is available at `/docs`.

## Authentication Layers

The app uses two local authentication mechanisms:

1. **Login session cookie:** `/auth/login` verifies
   `data/config/credentials.json` and sets an HttpOnly cookie. Account,
   model, and component-discovery endpoints require this cookie.
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
| `POST` | `/chat` | Bearer key | Generate chat with optional document RAG, reranking, and compression |
| `POST` | `/documents/upload` | Bearer key | Stage a document for one conversation |
| `POST` | `/documents/{document_id}/process` | Bearer key | Extract text and chunk a staged document |
| `POST` | `/documents/{document_id}/index` | Bearer key | Embed and index one processed document |
| `POST` | `/documents/search` | Bearer key | Search indexed document chunks without chat |
| `GET` | `/documents` | Bearer key | List documents for one conversation |
| `GET` | `/documents/indexes` | Bearer key | List vector collections for one conversation |
| `DELETE` | `/documents/indexes/{collection_id}` | Bearer key | Delete one vector collection |
| `GET` | `/documents/{document_id}` | Bearer key | Get document metadata |
| `GET` | `/documents/{document_id}/chunks` | Bearer key | Get processed document chunks |
| `POST` | `/repos/index-local` | Bearer key | Index a local repository with legacy keyword RAG |
| `POST` | `/repos/ask` | Bearer key | Ask a grounded question against a repository index |

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

Check or end the session:

```bash
curl -b session.cookies http://localhost:8000/auth/me
curl -b session.cookies -X POST http://localhost:8000/auth/logout
```

Invalid credentials return `401`. A missing or malformed credentials file
returns `503` with a local setup message.

## Account API Key

Save a local key. Short keys are accepted for testing, but a longer private
key is recommended for normal use:

```bash
curl -b session.cookies -X PUT http://localhost:8000/account/api-key \
  -H "Content-Type: application/json" \
  -d '{"api_key":"your-private-api-key"}'
```

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
    ]
  }'
```

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
`.txt`, `.md`, and `.pdf`. PDFs require an available parser such as PyMuPDF or
pdfplumber inside the backend runtime.

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

The current phase persists vectors in the local JSON store even when the
selected `vectorDatabase` records a future backend such as `chroma`.

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

## RAG, Reranking, and Compression

Document RAG is attempted when the resolved RAG pipeline is one of `hybrid`,
`reranked`, `graph`, or `agentic`, or when request `ragOptions.enabled` asks
for retrieval. Current retrieval uses local embeddings and JSON vector search.

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
`indexed_files`, and `indexed_chunks`. Index files are stored beneath
`DATA_DIRECTORY/indexes`.

Supported extensions are `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.md`, `.json`,
`.yaml`, `.yml`, `.html`, and `.css`. `.git`, `node_modules`, `.venv`,
`__pycache__`, `dist`, and `build` directories are ignored.

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

Response:

```json
{
  "answer": "The functions are implemented in sample_app/calculator.py.",
  "sources": ["app.py", "sample_app/calculator.py"]
}
```

## Security Notes

- Do not expose these endpoints directly to the public internet.
- Use HTTPS before sending cookies or Bearer keys across an untrusted network.
- The session cookie is HttpOnly and SameSite=Lax, but local HTTP is not
  encrypted.
- An authenticated Bearer caller can upload documents and index paths readable
  by the backend.
- Component discovery may show local packages or binaries available in the
  backend runtime.
- Model files are never downloaded or deleted by the application.
