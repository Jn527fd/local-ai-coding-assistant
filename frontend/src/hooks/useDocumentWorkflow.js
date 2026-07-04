import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getJob,
  listDocumentIndexes,
  listDocuments,
  searchDocuments,
  startIndexDocumentJob,
  startProcessDocumentJob,
  uploadDocument,
} from "../api.js";
import { normalizeConversationSettings } from "../chatState.js";

export const SUPPORTED_DOCUMENT_EXTENSIONS = [
  "txt",
  "md",
  "pdf",
  "docx",
  "html",
  "htm",
  "csv",
  "tsv",
];

const SUPPORTED_DOCUMENT_MESSAGE =
  "Only .txt, .md, .pdf, .docx, .html, .csv, and .tsv files are supported.";

export function useDocumentWorkflow({
  activeChat,
  apiKey,
  authState,
  defaultConversationSettings,
  showToast,
}) {
  const [documentsByChat, setDocumentsByChat] = useState({});
  const [documentIndexesByChat, setDocumentIndexesByChat] = useState({});
  const [documentBusy, setDocumentBusy] = useState(false);
  const [documentJobProgress, setDocumentJobProgress] = useState(null);
  const [documentError, setDocumentError] = useState("");
  const [indexingDocumentId, setIndexingDocumentId] = useState("");
  const [documentSearchQuery, setDocumentSearchQuery] = useState("");
  const [documentSearchResults, setDocumentSearchResults] = useState([]);
  const [documentSearchWarnings, setDocumentSearchWarnings] = useState([]);
  const [documentSearchBusy, setDocumentSearchBusy] = useState(false);
  const [documentSearchError, setDocumentSearchError] = useState("");

  const activeChatId = activeChat?.id || "";
  const activeDocuments = useMemo(
    () => documentsByChat[activeChatId] || [],
    [activeChatId, documentsByChat],
  );
  const activeDocumentIndexes = useMemo(
    () => documentIndexesByChat[activeChatId] || [],
    [activeChatId, documentIndexesByChat],
  );

  const refreshDocuments = useCallback(
    async (conversationId) => {
      if (!apiKey || !conversationId) {
        return [];
      }

      try {
        const result = await listDocuments(apiKey, conversationId);
        const documents = Array.isArray(result?.documents) ? result.documents : [];
        setDocumentsByChat((current) => ({
          ...current,
          [conversationId]: documents,
        }));
        return documents;
      } catch (error) {
        setDocumentError(error.message);
        return [];
      }
    },
    [apiKey],
  );

  const refreshDocumentIndexes = useCallback(
    async (conversationId) => {
      if (!apiKey || !conversationId) {
        return [];
      }

      try {
        const result = await listDocumentIndexes(apiKey, conversationId);
        const indexes = Array.isArray(result?.indexes) ? result.indexes : [];
        setDocumentIndexesByChat((current) => ({
          ...current,
          [conversationId]: indexes,
        }));
        return indexes;
      } catch (error) {
        setDocumentSearchError(error.message);
        return [];
      }
    },
    [apiKey],
  );

  const clearSearchState = useCallback(() => {
    setDocumentSearchQuery("");
    setDocumentSearchResults([]);
    setDocumentSearchWarnings([]);
    setDocumentSearchError("");
  }, []);

  const resetAllDocuments = useCallback(() => {
    setDocumentsByChat({});
    setDocumentIndexesByChat({});
    setDocumentBusy(false);
    setDocumentJobProgress(null);
    setDocumentError("");
    setIndexingDocumentId("");
    clearSearchState();
    setDocumentSearchBusy(false);
  }, [clearSearchState]);

  const rememberDocument = useCallback((conversationId, document) => {
    if (!conversationId || !document?.documentId) {
      return;
    }

    setDocumentsByChat((current) => {
      const existing = current[conversationId] || [];
      const withoutDocument = existing.filter(
        (item) => item.documentId !== document.documentId,
      );
      return {
        ...current,
        [conversationId]: [document, ...withoutDocument],
      };
    });
  }, []);

  const waitForJob = useCallback(
    async (jobId, label) => {
      let lastJob = null;
      for (let attempt = 0; attempt < 120; attempt += 1) {
        const payload = await getJob(apiKey, jobId);
        const job = payload?.job || payload;
        lastJob = job;
        setDocumentJobProgress({
          id: job.id,
          label,
          state: job.state,
          progress: job.progress || 0,
          message: job.message || label,
        });
        if (["succeeded", "failed", "cancelled"].includes(job.state)) {
          return job;
        }
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
      throw new Error(
        `${label} is still running. Check the job status and try again.`,
      );
    },
    [apiKey],
  );

  const handleUploadDocument = useCallback(
    async (file) => {
      if (!apiKey) {
        setDocumentError("Save and verify your API key before uploading documents.");
        return false;
      }

      if (!activeChat) {
        setDocumentError("Create a chat before uploading documents.");
        return false;
      }

      const extension = file.name.split(".").pop()?.toLowerCase() || "";
      if (!SUPPORTED_DOCUMENT_EXTENSIONS.includes(extension)) {
        setDocumentError(SUPPORTED_DOCUMENT_MESSAGE);
        return false;
      }

      const conversationId = activeChat.id;
      const conversationSettings = normalizeConversationSettings(
        activeChat.settings,
        defaultConversationSettings,
      );

      setDocumentBusy(true);
      setDocumentError("");

      try {
        const uploaded = await uploadDocument(
          apiKey,
          conversationId,
          file,
          conversationSettings,
        );
        rememberDocument(conversationId, uploaded);

        const queued = await startProcessDocumentJob(
          apiKey,
          uploaded.documentId,
          conversationId,
          conversationSettings,
        );
        const processJob = await waitForJob(
          queued.job.id,
          "Processing document",
        );
        if (processJob.state !== "succeeded") {
          throw new Error(
            processJob.error || processJob.message || "Document processing failed.",
          );
        }
        const processed = processJob.result || {};
        const processedDocument = processed.document || uploaded;
        rememberDocument(conversationId, processedDocument);
        await refreshDocuments(conversationId);

        if (processed.status === "processed") {
          showToast(
            `${processedDocument.originalFilename || file.name} processed (${processed.chunkCount || 0} chunks).`,
            "success",
          );
        } else {
          setDocumentError(processed.error || "Document processing failed.");
          showToast("Document uploaded, but processing failed.", "error");
        }
        return processed.status === "processed";
      } catch (error) {
        setDocumentError(error.message);
        showToast("Document upload failed.", "error");
        return false;
      } finally {
        setDocumentBusy(false);
        setDocumentJobProgress(null);
      }
    },
    [
      activeChat,
      apiKey,
      defaultConversationSettings,
      refreshDocuments,
      rememberDocument,
      showToast,
      waitForJob,
    ],
  );

  const handleIndexDocument = useCallback(
    async (document) => {
      if (!apiKey) {
        setDocumentSearchError("Save and verify your API key before indexing documents.");
        return false;
      }

      if (!activeChat || !document?.documentId) {
        return false;
      }

      if (document.status !== "processed") {
        setDocumentSearchError("Process the document before indexing it.");
        return false;
      }

      const conversationSettings = normalizeConversationSettings(
        activeChat.settings,
        defaultConversationSettings,
      );
      setIndexingDocumentId(document.documentId);
      setDocumentSearchError("");

      try {
        const queued = await startIndexDocumentJob(
          apiKey,
          document.documentId,
          activeChat.id,
          conversationSettings,
        );
        const indexJob = await waitForJob(queued.job.id, "Indexing document");
        if (indexJob.state !== "succeeded") {
          throw new Error(
            indexJob.error || indexJob.message || "Document indexing failed.",
          );
        }
        const result = indexJob.result || {};
        await refreshDocumentIndexes(activeChat.id);
        showToast(
          `${document.originalFilename || "Document"} indexed (${result.indexedChunks || 0} chunks).`,
          "success",
        );
        return true;
      } catch (error) {
        setDocumentSearchError(error.message);
        showToast("Document indexing failed.", "error");
        return false;
      } finally {
        setIndexingDocumentId("");
        setDocumentJobProgress(null);
      }
    },
    [
      activeChat,
      apiKey,
      defaultConversationSettings,
      refreshDocumentIndexes,
      showToast,
      waitForJob,
    ],
  );

  const handleSearchDocuments = useCallback(async () => {
    const query = documentSearchQuery.trim();
    if (!query) {
      setDocumentSearchError("");
      setDocumentSearchResults([]);
      return false;
    }

    if (!apiKey) {
      setDocumentSearchError("Save and verify your API key before searching documents.");
      return false;
    }

    if (!activeChat) {
      setDocumentSearchError("Create a chat before searching documents.");
      return false;
    }

    const conversationSettings = normalizeConversationSettings(
      activeChat.settings,
      defaultConversationSettings,
    );
    setDocumentSearchBusy(true);
    setDocumentSearchError("");
    setDocumentSearchWarnings([]);

    try {
      const result = await searchDocuments(
        apiKey,
        activeChat.id,
        query,
        conversationSettings,
        { topK: 5 },
      );
      setDocumentSearchResults(
        Array.isArray(result?.results) ? result.results : [],
      );
      setDocumentSearchWarnings(
        Array.isArray(result?.warnings) ? result.warnings : [],
      );
      return true;
    } catch (error) {
      setDocumentSearchError(error.message);
      setDocumentSearchResults([]);
      return false;
    } finally {
      setDocumentSearchBusy(false);
    }
  }, [
    activeChat,
    apiKey,
    defaultConversationSettings,
    documentSearchQuery,
  ]);

  useEffect(() => {
    if (authState !== "authenticated" || !activeChatId || !apiKey) {
      return;
    }

    refreshDocuments(activeChatId);
    refreshDocumentIndexes(activeChatId);
    setDocumentSearchResults([]);
    setDocumentSearchWarnings([]);
    setDocumentSearchError("");
  }, [
    activeChatId,
    apiKey,
    authState,
    refreshDocumentIndexes,
    refreshDocuments,
  ]);

  return {
    activeDocumentIndexes,
    activeDocuments,
    clearDocumentSearchState: clearSearchState,
    documentBusy,
    documentError,
    documentJobProgress,
    documentSearchBusy,
    documentSearchError,
    documentSearchQuery,
    documentSearchResults,
    documentSearchWarnings,
    handleIndexDocument,
    handleSearchDocuments,
    handleUploadDocument,
    indexingDocumentId,
    refreshDocumentIndexes,
    refreshDocuments,
    resetAllDocuments,
    setDocumentError,
    setDocumentSearchError,
    setDocumentSearchQuery,
  };
}
