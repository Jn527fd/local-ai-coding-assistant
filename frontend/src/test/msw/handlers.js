import { delay, http, HttpResponse } from "msw";

export const API_BASE_URL = "*";

const models = [
  {
    name: "qwen3:4b",
    label: "qwen3:4b",
    parameters_billion: 4,
    parameter_size: "4B",
    size_bytes: 2_600_000_000,
    size_display: "2.4 GiB",
    family: "qwen3",
    quantization_level: "Q4_K_M",
  },
  {
    name: "llama3.2:3b",
    label: "llama3.2:3b",
    parameters_billion: 3,
    parameter_size: "3B",
    size_bytes: 2_100_000_000,
    size_display: "2.0 GiB",
    family: "llama",
    quantization_level: "Q4_K_M",
  },
];

export function modelStatus(overrides = {}) {
  return {
    active_model: "qwen3:4b",
    supported_models: models,
    installed_models: models.map((model) => model.name),
    ollama_connected: true,
    switching: false,
    target_model: null,
    phase: "idle",
    progress: null,
    message: "Ready",
    error: null,
    warning: null,
    ...overrides,
  };
}

export function componentCapabilities(overrides = {}) {
  return {
    llmModels: models.map((model) => ({
      id: model.name,
      label: model.label,
      type: "llmModel",
      available: true,
      source: "ollama",
      name: model.name,
      size: model.size_bytes,
      implementationStatus: "implemented",
      implemented: true,
      execution: {
        status: "implemented",
        implemented: true,
        mode: "direct",
        description: "Model can be used through the local Ollama provider.",
      },
      details: {
        family: model.family,
        parameterSize: model.parameter_size,
        quantizationLevel: model.quantization_level,
      },
    })),
    embedderModels: [
      {
        id: "nomic-embed-text:latest",
        label: "nomic-embed-text:latest",
        type: "embedderModel",
        available: true,
        source: "ollama",
        name: "nomic-embed-text:latest",
        implementationStatus: "implemented",
        implemented: true,
        execution: {
          status: "implemented",
          implemented: true,
          mode: "direct",
          description: "Model can be used through the local Ollama provider.",
        },
      },
    ],
    rerankerModels: [],
    visionModels: [],
    ocrEngines: [
      {
        id: "none",
        label: "None",
        type: "ocrEngine",
        available: true,
        source: "builtin",
        implementationStatus: "implemented",
        implemented: true,
        execution: {
          status: "implemented",
          implemented: true,
          mode: "disabled",
          description: "Disables OCR for document processing.",
        },
      },
    ],
    pdfParsers: [
      {
        id: "pymupdf",
        label: "PyMuPDF",
        type: "pdfParser",
        available: true,
        source: "local",
        implementationStatus: "implemented",
        implemented: true,
        execution: {
          status: "implemented",
          implemented: true,
          mode: "direct",
          description: "Extracts selectable PDF text with PyMuPDF.",
        },
      },
    ],
    chunkers: [
      {
        id: "fixed",
        label: "Fixed",
        type: "chunker",
        available: true,
        implementationStatus: "implemented",
        implemented: true,
        execution: {
          status: "implemented",
          implemented: true,
          mode: "direct",
          description: "Splits documents into fixed-size character windows.",
        },
      },
      {
        id: "recursive",
        label: "Recursive",
        type: "chunker",
        available: true,
        implementationStatus: "implemented",
        implemented: true,
        execution: {
          status: "implemented",
          implemented: true,
          mode: "direct",
          description: "Splits documents on paragraph-aware recursive boundaries.",
        },
      },
    ],
    vectorDatabases: [
      {
        id: "chroma",
        label: "Chroma",
        type: "vectorDatabase",
        available: true,
        implementationStatus: "fallback",
        implemented: false,
        execution: {
          status: "fallback",
          implemented: false,
          mode: "fallback",
          description: "Selection is recorded; vectors are stored in the local JSON index.",
        },
      },
    ],
    ragPipelines: [
      {
        id: "basic",
        label: "Basic",
        type: "ragPipeline",
        available: true,
        implementationStatus: "implemented",
        implemented: true,
        execution: {
          status: "implemented",
          implemented: true,
          mode: "direct",
          description: "Uses local vector retrieval when document RAG is enabled.",
        },
      },
    ],
    contextCompressors: [
      {
        id: "none",
        label: "None",
        type: "contextCompressor",
        available: true,
        implementationStatus: "implemented",
        implemented: true,
        execution: {
          status: "implemented",
          implemented: true,
          mode: "direct",
          description: "Leaves chat history and retrieved context unchanged.",
        },
      },
    ],
    unknownOllamaModels: [],
    ...overrides,
  };
}

const documentsByConversation = new Map();
const indexesByConversation = new Map();

function rememberDocument(conversationId, document) {
  const existing = documentsByConversation.get(conversationId) || [];
  const withoutDocument = existing.filter(
    (item) => item.documentId !== document.documentId,
  );
  documentsByConversation.set(conversationId, [document, ...withoutDocument]);
}

function rememberIndex(conversationId, collection) {
  const existing = indexesByConversation.get(conversationId) || [];
  const withoutCollection = existing.filter(
    (item) => item.collectionId !== collection.collectionId,
  );
  indexesByConversation.set(conversationId, [collection, ...withoutCollection]);
}

export const runtimeOnlineHandlers = [
  http.get(`${API_BASE_URL}/health`, () => HttpResponse.json({ status: "ok" })),
  http.post(`${API_BASE_URL}/auth/login`, () =>
    HttpResponse.json({ username: "test-user" }),
  ),
  http.get(`${API_BASE_URL}/auth/me`, () =>
    HttpResponse.json({ username: "test-user" }),
  ),
  http.post(`${API_BASE_URL}/auth/logout`, () => new HttpResponse(null, { status: 204 })),
  http.get(`${API_BASE_URL}/account/status`, () =>
    HttpResponse.json({
      username: "test-user",
      api_key_configured: true,
      api_key_active: true,
    }),
  ),
  http.put(`${API_BASE_URL}/account/api-key`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      username: "test-user",
      api_key_configured: Boolean(body.api_key),
      api_key_active: Boolean(body.api_key),
    });
  }),
  http.get(`${API_BASE_URL}/models/status`, () => HttpResponse.json(modelStatus())),
  http.get(`${API_BASE_URL}/components/capabilities`, () =>
    HttpResponse.json(componentCapabilities()),
  ),
  http.post(`${API_BASE_URL}/models/switch`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json(
      { accepted: true, model: body.model || "qwen3:4b" },
      { status: 202 },
    );
  }),
  http.post(`${API_BASE_URL}/chat/stream`, async ({ request }) => {
    const body = await request.json();
    await delay(220);
    const answer = `Fake streaming answer for: ${body.message}`;
    const metadata = {
      model: "qwen3:4b",
      ragUsed: true,
      ragWarnings: ["Document context skipped one stale index."],
      rerankingUsed: true,
      rerankerModel: "bge-reranker:latest",
      rerankWarnings: ["Reranker skipped one low-confidence score."],
      compressionUsed: true,
      compressorMode: "token",
      compressionWarnings: ["Token compression trimmed 2 older history messages."],
      compressionStats: {
        originalCharEstimate: 18000,
        compressedCharEstimate: 9000,
        originalTokenEstimate: 4500,
        compressedTokenEstimate: 2250,
        messagesTrimmed: 2,
        contextTrimmed: 0,
        summaryGenerated: false,
      },
      visionUsed: false,
      visionWarnings: [],
      sources: [
        {
          sourceNumber: 1,
          documentId: "doc-1",
          documentName: "notes.txt",
          chunkId: "chunk-1",
          chunkIndex: 0,
          score: 0.91,
          vectorScore: 0.51,
          rerankScore: 0.91,
          finalRank: 1,
          textPreview: "The FastAPI app is created in backend/app/main.py.",
        },
        "backend/app/main.py",
      ],
    };
    return new HttpResponse(
      [
        `event: progress\ndata: ${JSON.stringify({ stage: "generating" })}\n\n`,
        `event: metadata\ndata: ${JSON.stringify(metadata)}\n\n`,
        `event: token\ndata: ${JSON.stringify({ text: answer })}\n\n`,
        `event: done\ndata: ${JSON.stringify({ ...metadata, answer })}\n\n`,
      ].join(""),
      {
        headers: { "Content-Type": "text/event-stream" },
      },
    );
  }),
  http.post(`${API_BASE_URL}/chat`, async ({ request }) => {
    const body = await request.json();
    await delay(60);
    return HttpResponse.json({
      model: "qwen3:4b",
      answer: `Fake Ollama answer for: ${body.message}`,
      sources: ["backend/app/main.py", "frontend/src/App.jsx"],
    });
  }),
  http.post(`${API_BASE_URL}/documents/upload`, async ({ request }) => {
    const formData = await request.formData();
    const conversationId = String(formData.get("conversationId") || "chat-1");
    const file = formData.get("file");
    const document = {
      documentId:
        globalThis.crypto?.randomUUID?.() || `doc-${Date.now()}`,
      conversationId,
      originalFilename: file?.name || "Document",
      status: "uploaded",
      chunkCount: 0,
      createdAt: new Date().toISOString(),
    };
    rememberDocument(conversationId, document);
    return HttpResponse.json(document);
  }),
  http.post(`${API_BASE_URL}/documents/:documentId/process`, async ({ params, request }) => {
    const body = await request.json();
    const conversationId = body.conversationId || "chat-1";
    const existing = documentsByConversation
      .get(conversationId)
      ?.find((item) => item.documentId === params.documentId);
    const document = {
      ...(existing || {
        documentId: params.documentId,
        conversationId,
        originalFilename: "Document",
      }),
      status: "processed",
      chunkCount: 3,
      processedAt: new Date().toISOString(),
    };
    rememberDocument(conversationId, document);
    return HttpResponse.json({
      document,
      documentId: document.documentId,
      conversationId,
      status: "processed",
      chunkCount: 3,
      charLength: 120,
      warnings: [],
      error: null,
    });
  }),
  http.post(`${API_BASE_URL}/documents/:documentId/index`, async ({ params, request }) => {
    const body = await request.json();
    const conversationId = body.conversationId || "chat-1";
    const collection = {
      collectionId: "json-demo",
      conversationId,
      embedderModel:
        body.conversationSettings?.embedderModel || "nomic-embed-text:latest",
      vectorDatabase:
        body.conversationSettings?.vectorDatabase || "chroma",
      documentIds: [params.documentId],
      recordCount: 3,
      updatedAt: new Date().toISOString(),
      source: "json",
    };
    rememberIndex(conversationId, collection);
    return HttpResponse.json({
      collection,
      collectionId: collection.collectionId,
      conversationId,
      documentId: params.documentId,
      indexedChunks: 3,
      embedderModel: collection.embedderModel,
      vectorDatabase: collection.vectorDatabase,
      internalStore: "json",
      warning: "Using local JSON vector store.",
    });
  }),
  http.post(`${API_BASE_URL}/documents/search`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      conversationId: body.conversationId,
      query: body.query,
      embedderModel:
        body.conversationSettings?.embedderModel || "nomic-embed-text:latest",
      vectorDatabase:
        body.conversationSettings?.vectorDatabase || "chroma",
      topK: body.topK || 5,
      warnings: [],
      results: [
        {
          score: 0.91,
          collectionId: "json-demo",
          documentId: "doc-demo",
          documentName: "notes.txt",
          chunkId: "doc-demo:0",
          chunkIndex: 0,
          text: `Mock document result for ${body.query}`,
          metadata: { chunker: "recursive" },
        },
      ],
    });
  }),
  http.get(`${API_BASE_URL}/documents`, ({ request }) => {
    const url = new URL(request.url);
    const conversationId = url.searchParams.get("conversationId") || "";
    return HttpResponse.json({
      conversationId,
      documents: documentsByConversation.get(conversationId) || [],
    });
  }),
  http.get(`${API_BASE_URL}/documents/indexes`, ({ request }) => {
    const url = new URL(request.url);
    const conversationId = url.searchParams.get("conversationId") || "";
    return HttpResponse.json({
      conversationId,
      indexes: indexesByConversation.get(conversationId) || [],
    });
  }),
  http.delete(`${API_BASE_URL}/documents/indexes/:collectionId`, ({ params, request }) => {
    const url = new URL(request.url);
    const conversationId = url.searchParams.get("conversationId") || "";
    const existing = indexesByConversation.get(conversationId) || [];
    indexesByConversation.set(
      conversationId,
      existing.filter((item) => item.collectionId !== params.collectionId),
    );
    return HttpResponse.json({
      deleted: true,
      collectionId: params.collectionId,
      conversationId,
    });
  }),
  http.get(`${API_BASE_URL}/documents/:documentId`, ({ params, request }) => {
    const url = new URL(request.url);
    const conversationId = url.searchParams.get("conversationId") || "";
    const document = documentsByConversation
      .get(conversationId)
      ?.find((item) => item.documentId === params.documentId);
    return document
      ? HttpResponse.json(document)
      : HttpResponse.json({ detail: "Document was not found." }, { status: 404 });
  }),
  http.get(`${API_BASE_URL}/documents/:documentId/chunks`, ({ params, request }) => {
    const url = new URL(request.url);
    const conversationId = url.searchParams.get("conversationId") || "";
    return HttpResponse.json({
      documentId: params.documentId,
      conversationId,
      status: "processed",
      chunks: [
        {
          chunkId: `${params.documentId}:0`,
          documentId: params.documentId,
          conversationId,
          index: 0,
          text: "Mock document chunk",
          charStart: 0,
          charEnd: 19,
          charLength: 19,
          tokenEstimate: 5,
          metadata: { chunker: "recursive" },
        },
      ],
    });
  }),
  http.post(`${API_BASE_URL}/repos/index-local`, () =>
    HttpResponse.json({
      repo_name: "sample-code-repository",
      indexed_files: 9,
      indexed_chunks: 9,
    }),
  ),
  http.post(`${API_BASE_URL}/repos/ask`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      answer: `Grounded answer for ${body.repo_name}: ${body.question}`,
      sources: ["sample-code-repository/src/app.py"],
    });
  }),
  http.get(`${API_BASE_URL}/search`, () =>
    HttpResponse.json({
      results: [
        {
          path: "backend/app/routers/chat.py",
          line: 93,
          preview: "async def chat(",
        },
      ],
    }),
  ),
];

export const runtimeOfflineHandlers = [
  http.get(`${API_BASE_URL}/health`, () =>
    HttpResponse.json({ detail: "Backend unavailable" }, { status: 503 }),
  ),
  http.get(`${API_BASE_URL}/models/status`, () =>
    HttpResponse.json(modelStatus({ ollama_connected: false, error: "Ollama offline" })),
  ),
];

export const repositoryIndexingHandler = http.post(
  `${API_BASE_URL}/repos/index-local`,
  async () => {
    await delay(120);
    return HttpResponse.json({
      repo_name: "sample-code-repository",
      indexed_files: 9,
      indexed_chunks: 9,
    });
  },
);

export const emptyRepositoryHandler = http.post(
  `${API_BASE_URL}/repos/ask`,
  () => HttpResponse.json({ detail: "Repository is not indexed." }, { status: 404 }),
);

export const handlers = [...runtimeOnlineHandlers];
