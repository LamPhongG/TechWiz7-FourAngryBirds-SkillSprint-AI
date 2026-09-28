import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import * as store from "../services/documentStore";
import { processDocument } from "../services/documentProcessing";
import { sanitizeDocuments } from "../services/sanitize";
import { apiBlob, apiRequest, backendEnabled, uploadWithProgress } from "../services/apiClient";
import { mapChunks, mapDocument } from "../services/apiMappers";
import { useAuth } from "../hooks/useAuth";
import { compareVersions, computeLifecycle, familyOf, findCatalogEntry, normalizeVersion } from "../utils/documentValidation";
import { todayISO } from "../utils/helpers";

const DocumentsContext = createContext(null);

// Mode is fixed at build time (VITE_API_URL), so provider always invokes the same hook — adhering to React rules of hooks
const useDocumentSource = backendEnabled() ? useBackendDocuments : useBrowserDocuments;

export function DocumentsProvider({ children }) {
  const { records, loading, error, progress, processed, addDocuments, removeDocument, getFile, processDocuments } = useDocumentSource();

  // Attach lifecycle status (recomputed whenever list changes) + title from catalog
  const documents = useMemo(() => {
    const lifecycle = computeLifecycle(records, todayISO());
    return records
      .map(d => ({ ...d, title: d.title || findCatalogEntry(d.code)?.title?.replace(/\s*\(obsolete\)$/, "") || d.titleEn, ...lifecycle[d.id] }))
      .sort((a, b) => a.code.localeCompare(b.code) || compareVersions(b.version, a.version));
  }, [records]);

  const chunksByDocId = useMemo(
    () => Object.fromEntries(Object.entries(processed).map(([id, r]) => [id, r.chunks || []])),
    [processed]
  );

  const value = useMemo(() => ({
    documents,
    activeDocuments: documents.filter(d => d.status === "active"),
    loading,
    error,
    addDocuments,
    removeDocument,
    getFile,
    progress,
    processed,
    chunksByDocId,
    processDocuments,
  }), [documents, loading, error, addDocuments, removeDocument, getFile, progress, processed, chunksByDocId, processDocuments]);

  return <DocumentsContext.Provider value={value}>{children}</DocumentsContext.Provider>;
}

/** Documents stored in IndexedDB, extracted + chunked directly in the browser */
function useBrowserDocuments() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // id -> { percent, stage } for currently processing document; not persisted as it's session-specific
  const [progress, setProgress] = useState({});
  // id → { chunks, injection_flags, engine, page_count, ... }
  const [processed, setProcessed] = useState({});
  const inFlight = useRef(new Set());
  const autoStarted = useRef(false);

  const reload = useCallback(async () => {
    try {
      const list = sanitizeDocuments(await store.listDocuments());
      setRecords(list);
      const doneIds = list.filter(d => d.processing === "done").map(d => d.id);
      const results = await store.getProcessing(doneIds);
      setProcessed(Object.fromEntries(results.map(r => [r.id, {
        ...r,
        chunks: Array.isArray(r.chunks) ? r.chunks : [],
        injection_flags: Array.isArray(r.injection_flags) ? r.injection_flags : [],
      }])));
      setError(null);
      return list;
    } catch (e) {
      setError(e);
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  // Run sequentially: pdf.js and mammoth consume memory; processing 20 files in parallel may freeze tab
  const processDocuments = useCallback(async (docs) => {
    const queue = docs.filter(d => !inFlight.current.has(d.id));
    queue.forEach(d => inFlight.current.add(d.id));
    setProgress(prev => ({ ...prev, ...Object.fromEntries(queue.map(d => [d.id, { percent: 0, stage: "queued" }])) }));
    for (const doc of queue) {
      try {
        const blob = await store.getDocumentFile(doc.id);
        if (!blob) throw new Error("File not found");
        const result = await processDocument(doc, blob, p => setProgress(prev => ({ ...prev, [doc.id]: p })));
        await store.saveProcessing(doc.id, {
          processing: "done",
          processingEngine: result.engine,
          processedAt: result.processed_at,
          chunkCount: result.chunks.length,
          pageCount: result.page_count,
          injectionFlagCount: result.injection_flags.length,
          processingError: null,
        }, result);
      } catch (e) {
        await store.saveProcessing(doc.id, { processing: "failed", processingError: e.message }).catch(() => {});
      } finally {
        inFlight.current.delete(doc.id);
        setProgress(prev => {
          const next = { ...prev };
          delete next[doc.id];
          return next;
        });
      }
    }
    if (queue.length) await reload();
  }, [reload]);

  // Documents uploaded prior to processing step remain "pending" — backfill processing once on app load
  useEffect(() => {
    reload().then(list => {
      if (autoStarted.current) return;
      autoStarted.current = true;
      const pending = list.filter(d => d.processing === "pending");
      if (pending.length) processDocuments(pending);
    });
  }, [reload, processDocuments]);

  // drafts already validated with validateDraft; returns count of saved documents
  const addDocuments = useCallback(async (drafts, uploadedBy) => {
    const uploadedAt = new Date().toISOString();
    const entries = drafts.map(draft => {
      const code = draft.code.trim().toUpperCase();
      const titleEn = draft.titleEn.trim();
      return {
        file: draft.file,
        meta: {
          id: globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`,
          code,
          titleEn,
          family: familyOf({ code, titleEn }),
          category: draft.category,
          department: draft.department,
          version: normalizeVersion(draft.version),
          effectiveDate: draft.effectiveDate,
          expiryDate: draft.expiryDate || null,
          fileName: draft.file.name,
          ext: draft.ext,
          mimeType: draft.file.type,
          size: draft.file.size,
          hash: draft.hash,
          uploadedAt,
          uploadedBy,
          processing: "pending",
        },
      };
    });
    await store.saveDocuments(entries);
    await reload();
    // Non-blocking processing: upload modal closes immediately, progress displays in document table
    processDocuments(entries.map(e => e.meta));
    return entries.length;
  }, [reload, processDocuments]);

  const removeDocument = useCallback(async (id) => {
    await store.deleteDocument(id);
    await reload();
  }, [reload]);

  return { records, loading, error, progress, processed, addDocuments, removeDocument, getFile: store.getDocumentFile, processDocuments };
}

/** Documents managed by backend: upload, extraction, chunking, and injection scan performed on server */
function useBackendDocuments() {
  const { user } = useAuth();
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState({});
  const [processed, setProcessed] = useState({});
  // Chunks accessible only by HR / Reviewer / Admin (for audit); learners access content within learning path
  const canReadChunks = ["hr", "reviewer", "admin"].includes(user?.userRole);

  const reload = useCallback(async () => {
    if (!user) {
      setRecords([]);
      setProcessed({});
      setLoading(false);
      return [];
    }
    try {
      const list = (await apiRequest("/documents")).map(mapDocument);
      setRecords(list);
      if (canReadChunks) {
        const ready = list.filter(d => d.processing === "done");
        const results = await Promise.all(ready.map(d => apiRequest(`/documents/${d.id}/chunks`).then(mapChunks)));
        setProcessed(Object.fromEntries(ready.map((d, i) => [d.id, results[i]])));
      }
      setError(null);
      return list;
    } catch (e) {
      setError(e);
      return [];
    } finally {
      setLoading(false);
    }
  }, [user, canReadChunks]);

  useEffect(() => { reload(); }, [reload]);

  // Server processes within upload request, so await all before closing modal
  const addDocuments = useCallback(async (drafts) => {
    const failures = [];
    let saved = 0;
    for (const draft of drafts) {
      const form = new FormData();
      form.append("file", draft.file, draft.file.name);
      form.append("code", draft.code.trim().toUpperCase());
      form.append("title_en", draft.titleEn.trim());
      form.append("category", draft.category);
      form.append("department_code", draft.department);
      form.append("version", normalizeVersion(draft.version));
      form.append("effective_date", draft.effectiveDate);
      form.append("expiry_date", draft.expiryDate || "");
      try {
        await uploadWithProgress("/documents", form, ratio =>
          setProgress(prev => ({ ...prev, [draft.key]: { percent: Math.round(ratio * 90), stage: "upload" } })));
        saved++;
      } catch (e) {
        failures.push(`${draft.file.name}: ${e.message}`);
      } finally {
        setProgress(prev => {
          const next = { ...prev };
          delete next[draft.key];
          return next;
        });
      }
    }
    await reload();
    if (failures.length) throw new Error(failures.join("; "));
    return saved;
  }, [reload]);

  const removeDocument = useCallback(async (id) => {
    await apiRequest(`/documents/${id}`, { method: "DELETE" });
    await reload();
  }, [reload]);

  const getFile = useCallback(id => apiBlob(`/documents/${id}/file`), []);

  // "Retry" for failed document processing: server re-reads saved file
  const processDocuments = useCallback(async (docs) => {
    for (const doc of docs) {
      setProgress(prev => ({ ...prev, [doc.id]: { percent: 50, stage: "extract" } }));
      try {
        await apiRequest(`/documents/${doc.id}/process`, { method: "POST" });
      } finally {
        setProgress(prev => {
          const next = { ...prev };
          delete next[doc.id];
          return next;
        });
      }
    }
    await reload();
  }, [reload]);

  return { records, loading, error, progress, processed, addDocuments, removeDocument, getFile, processDocuments };
}

export function useDocuments() {
  const ctx = useContext(DocumentsContext);
  if (!ctx) throw new Error("useDocuments must be used inside <DocumentsProvider>");
  return ctx;
}

export async function openStoredFile(getFile, doc, { download = false, page = null } = {}) {
  const blob = await getFile(doc.id);
  if (!blob) throw new Error("File not found");
  const url = URL.createObjectURL(blob);
  if (download) {
    const a = document.createElement("a");
    a.href = url;
    a.download = doc.fileName;
    document.body.appendChild(a);
    a.click();
    a.remove();
  } else {
    // Browser PDF viewer understands #page=N — jumps directly to cited page
    window.open(page && doc.ext === "pdf" ? `${url}#page=${page}` : url, "_blank", "noopener");
  }
  // Allow new tab time to read blob before revoking URL
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
