import { beforeEach, describe, expect, it } from "vitest"
import { createDefaultConversationDraft } from "../../domain/defaults"
import {
  createMockServices,
  type MockServiceBundle,
} from "./createMockServices"

describe("mock application services", () => {
  let bundle: MockServiceBundle

  beforeEach(() => {
    sessionStorage.clear()
    localStorage.clear()
    bundle = createMockServices()
    bundle.control.setLatency(0)
  })

  it("validates login and restores and clears the session", async () => {
    await expect(
      bundle.services.auth.signIn({ username: "wrong", password: "wrong" }),
    ).rejects.toMatchObject({ code: "unauthorized" })
    const session = await bundle.services.auth.signIn({
      username: "test",
      password: "test",
    })
    expect(await bundle.services.auth.restoreSession()).toEqual(session)
    await bundle.services.auth.signOut()
    expect(await bundle.services.auth.restoreSession()).toBeNull()
  })

  it("stores and checks a mock API key", async () => {
    expect(bundle.services.account.getStoredApiKey()).toBe("local-mock-key")
    await expect(bundle.services.account.getStatus()).resolves.toMatchObject({
      username: "test",
      apiKeyConfigured: true,
      apiKeyActive: true,
    })

    bundle.services.account.setStoredApiKey("next-key")
    expect(bundle.services.account.getStoredApiKey()).toBe("next-key")
    await expect(
      bundle.services.account.getStatus("wrong"),
    ).resolves.toMatchObject({
      apiKeyConfigured: true,
      apiKeyActive: false,
    })
    await expect(
      bundle.services.account.updateApiKey("saved-key"),
    ).resolves.toEqual({
      username: "test",
      apiKeyConfigured: true,
      apiKeyActive: true,
    })
  })

  it("serves local capability fixtures in mock mode", async () => {
    const capabilities = await bundle.services.capabilities.list()
    expect(capabilities.llmModels).toContainEqual(
      expect.objectContaining({ id: "llama3.2:3b", available: true }),
    )
    expect(capabilities.embedderModels).toContainEqual(
      expect.objectContaining({ id: "all-minilm", available: true }),
    )
    expect(capabilities.ocrEngines).toContainEqual(
      expect.objectContaining({ id: "none", available: true }),
    )
    expect(capabilities.ocrEngines).toContainEqual(
      expect.objectContaining({ id: "paddleocr", available: true }),
    )
    expect(capabilities.pdfParsers).toContainEqual(
      expect.objectContaining({ id: "docling", available: true }),
    )
  })

  it("serves redacted diagnostics fixtures in mock mode", async () => {
    await expect(
      bundle.services.diagnostics.getStatus(),
    ).resolves.toMatchObject({
      runtime: { status: "ok", mode: "mock" },
      jobs: { running: 0 },
    })
    const exported = await bundle.services.diagnostics.exportSupportBundle()
    expect(exported.filename).toBe("localchat-support-bundle-mock.json")
    expect(JSON.parse(exported.content)).toMatchObject({
      redacted: true,
      redactionPolicy: expect.stringMatching(/secrets/i),
      diagnostics: {
        retrieval: { vectorDatabase: "json" },
      },
    })
  })

  it("handles signup failures and the complete email verification flow", async () => {
    await expect(
      bundle.services.auth.requestEmailVerification("other@example.com"),
    ).rejects.toMatchObject({ code: "validation" })
    await bundle.services.auth.requestEmailVerification("test@email.com")
    await expect(
      bundle.services.auth.verifyEmailCode({
        email: "test@email.com",
        code: "00000",
      }),
    ).rejects.toMatchObject({ code: "validation" })
    await bundle.services.auth.verifyEmailCode({
      email: "test@email.com",
      code: "12345",
    })
    await expect(
      bundle.services.auth.createAccount({
        email: "test@email.com",
        password: "Strong!123",
      }),
    ).resolves.toMatchObject({ user: { email: "test@email.com" } })
  })

  it("keeps prompt, model, source, and temporary settings isolated by conversation", async () => {
    const draft = createDefaultConversationDraft()
    const first = await bundle.services.conversations.create({
      title: "First",
      ...draft,
    })
    const second = await bundle.services.conversations.create({
      title: "Second",
      ...draft,
    })

    await bundle.services.conversations.updateConfiguration(first.id, {
      systemPrompt: "Only first",
      sourceIds: ["product-roadmap"],
      modelConfiguration: { llmModel: "custom-model" },
      temporary: true,
    })

    expect(await bundle.services.conversations.get(first.id)).toMatchObject({
      systemPrompt: "Only first",
      sourceIds: ["product-roadmap"],
      temporary: true,
      modelConfiguration: { llmModel: "custom-model" },
    })
    expect(await bundle.services.conversations.get(second.id)).toMatchObject({
      systemPrompt: "",
      sourceIds: [],
      temporary: false,
      modelConfiguration: { llmModel: "llama3.2:3b" },
    })
  })

  it("emits pending, streaming, and completed message states", async () => {
    const conversation = await bundle.services.conversations.create({
      ...createDefaultConversationDraft(),
    })
    const events = []
    for await (const event of bundle.services.messages.stream({
      conversationId: conversation.id,
      content: "Hello",
      attachmentIds: [],
    }))
      events.push(event)

    expect(events[0]).toMatchObject({
      type: "accepted",
      assistantMessage: { status: "pending" },
    })
    expect(events.some((event) => event.type === "delta")).toBe(true)
    expect(events.at(-1)).toMatchObject({
      type: "complete",
      message: { status: "complete" },
    })
  })

  it("exposes failure and retry recovery states", async () => {
    const conversation = await bundle.services.conversations.create({
      ...createDefaultConversationDraft(),
    })
    const events = []
    for await (const event of bundle.services.messages.stream({
      conversationId: conversation.id,
      content: "[fail]",
      attachmentIds: [],
    }))
      events.push(event)
    const failure = events.at(-1)
    expect(failure).toMatchObject({
      type: "failed",
      message: { status: "failed" },
    })
    if (!failure || failure.type !== "failed")
      throw new Error("Expected failed event")
    await expect(
      bundle.services.messages.retry(conversation.id, failure.message.id),
    ).resolves.toMatchObject({ status: "complete", error: undefined })
  })

  it("renames and deletes conversations while preserving failed deletes", async () => {
    const conversation = await bundle.services.conversations.create({
      title: "Before",
      ...createDefaultConversationDraft(),
    })
    await expect(
      bundle.services.conversations.rename(conversation.id, "After"),
    ).resolves.toMatchObject({ title: "After" })
    bundle.control.failNext("conversations.delete")
    await expect(
      bundle.services.conversations.delete(conversation.id),
    ).rejects.toBeTruthy()
    await expect(
      bundle.services.conversations.get(conversation.id),
    ).resolves.toMatchObject({ title: "After" })
    await bundle.services.conversations.delete(conversation.id)
    await expect(
      bundle.services.conversations.get(conversation.id),
    ).rejects.toMatchObject({ code: "not_found" })
  })

  it("restores saved conversations and messages in a new service instance", async () => {
    const conversation = await bundle.services.conversations.create({
      title: "Reload-safe chat",
      ...createDefaultConversationDraft(),
    })
    await bundle.services.messages.send({
      conversationId: conversation.id,
      content: "Persist this message",
      attachmentIds: [],
    })

    const reloaded = createMockServices()
    reloaded.control.setLatency(0)

    await expect(
      reloaded.services.conversations.get(conversation.id),
    ).resolves.toMatchObject({
      id: conversation.id,
      title: "Reload-safe chat",
      messages: [
        { role: "user", content: "Persist this message" },
        { role: "assistant", status: "complete" },
      ],
    })
  })

  it("does not restore temporary conversations", async () => {
    const temporary = await bundle.services.conversations.create({
      title: "Temporary",
      ...createDefaultConversationDraft(),
      temporary: true,
    })

    const reloaded = createMockServices()
    reloaded.control.setLatency(0)

    await expect(
      reloaded.services.conversations.get(temporary.id),
    ).rejects.toMatchObject({ code: "not_found" })
  })

  it("restores an interrupted response as stopped and retryable", async () => {
    const conversation = await bundle.services.conversations.create({
      ...createDefaultConversationDraft(),
    })
    const stream = bundle.services.messages.stream({
      conversationId: conversation.id,
      content: "Start a response",
      attachmentIds: [],
    })
    const iterator = stream[Symbol.asyncIterator]()
    await iterator.next()

    const reloaded = createMockServices()
    reloaded.control.setLatency(0)
    const restored = await reloaded.services.conversations.get(conversation.id)

    expect(restored.messages.at(-1)).toMatchObject({
      role: "assistant",
      status: "stopped",
      error: "Response interrupted by page reload. Retry to continue.",
    })
  })

  it("uploads, retries, selects through configuration, and deletes sources", async () => {
    const [failed] = await bundle.services.sources.upload([
      new File(["data"], "fail-notes.txt", { type: "text/plain" }),
    ])
    expect(failed.status).toBe("failed")
    expect(await bundle.services.sources.retry(failed.id)).toMatchObject({
      status: "ready",
    })
    const conversation = await bundle.services.conversations.create({
      ...createDefaultConversationDraft(),
    })
    await bundle.services.conversations.updateConfiguration(conversation.id, {
      sourceIds: [failed.id],
    })
    await bundle.services.sources.delete(failed.id)
    expect(
      (await bundle.services.conversations.get(conversation.id)).sourceIds,
    ).toEqual([])
  })

  it("loads, updates, and exports a profile", async () => {
    const loaded = await bundle.services.profile.load()
    expect(loaded.profile).toMatchObject({
      id: "usr-local-7f2a91",
      displayName: "Taylor Morgan",
      accountType: "member",
    })

    const updated = await bundle.services.profile.update({
      displayName: "Updated User",
      handle: "updated.user",
      preferredName: "Updated",
      role: "Engineering",
      about: "Updated locally",
      preferredLanguage: "en-GB",
      responsePreference: "concise",
    })
    expect(updated.profile).toMatchObject({
      displayName: "Updated User",
      handle: "updated.user",
      responsePreference: "concise",
    })

    const reloaded = createMockServices()
    reloaded.control.setLatency(0)
    await expect(reloaded.services.profile.load()).resolves.toMatchObject({
      profile: { displayName: "Updated User", handle: "updated.user" },
    })

    const exported = await bundle.services.profile.exportData()
    expect(JSON.parse(exported.content)).toMatchObject({
      displayName: "Updated User",
    })
    await expect(bundle.services.profile.load()).resolves.toMatchObject({
      profile: { displayName: "Updated User" },
    })
  })
})
