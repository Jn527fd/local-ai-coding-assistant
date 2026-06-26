import { delay, http, HttpResponse } from "msw";

export const API_BASE_URL = "http://localhost:8000";

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
  http.post(`${API_BASE_URL}/models/switch`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json(
      { accepted: true, model: body.model || "qwen3:4b" },
      { status: 202 },
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
