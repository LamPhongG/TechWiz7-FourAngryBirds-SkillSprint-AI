// Browser-side document store (IndexedDB)
// Metadata, file content, and chunk extraction results are stored in 3 separate object stores so listing does not read blobs.
// Used when operating without backend; backend mode is handled via useBackendDocuments (contexts/DocumentsContext.jsx).
const DB_NAME = "skillsprint-ai";
const DB_VERSION = 2;
const META_STORE = "documents";
const FILE_STORE = "files";
const CHUNK_STORE = "chunks";

let dbPromise = null;

function openDb() {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve, reject) => {
    if (typeof indexedDB === "undefined") {
      reject(new Error("IndexedDB is not available in this browser"));
      return;
    }
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(META_STORE)) db.createObjectStore(META_STORE, { keyPath: "id" });
      if (!db.objectStoreNames.contains(FILE_STORE)) db.createObjectStore(FILE_STORE, { keyPath: "id" });
      // v2: extraction results (chunks + injection flags) indexed by document ID
      if (!db.objectStoreNames.contains(CHUNK_STORE)) db.createObjectStore(CHUNK_STORE, { keyPath: "id" });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
  // Allow retry on subsequent calls if opening failed this time
  dbPromise.catch(() => { dbPromise = null; });
  return dbPromise;
}

function done(tx) {
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error || new Error("Transaction aborted"));
  });
}

export async function listDocuments() {
  const db = await openDb();
  const tx = db.transaction(META_STORE, "readonly");
  const request = tx.objectStore(META_STORE).getAll();
  await done(tx);
  return request.result || [];
}

// Save multiple documents in a single transaction: either all succeed or none are committed
export async function saveDocuments(entries) {
  const db = await openDb();
  const tx = db.transaction([META_STORE, FILE_STORE], "readwrite");
  for (const { meta, file } of entries) {
    tx.objectStore(META_STORE).put(meta);
    tx.objectStore(FILE_STORE).put({ id: meta.id, blob: file });
  }
  await done(tx);
}

export async function getDocumentFile(id) {
  const db = await openDb();
  const tx = db.transaction(FILE_STORE, "readonly");
  const request = tx.objectStore(FILE_STORE).get(id);
  await done(tx);
  return request.result?.blob ?? null;
}

export async function deleteDocument(id) {
  const db = await openDb();
  const tx = db.transaction([META_STORE, FILE_STORE, CHUNK_STORE], "readwrite");
  tx.objectStore(META_STORE).delete(id);
  tx.objectStore(FILE_STORE).delete(id);
  tx.objectStore(CHUNK_STORE).delete(id);
  await done(tx);
}

// Update metadata and processing results in the same transaction to keep them synchronized
export async function saveProcessing(id, metaPatch, result = null) {
  const db = await openDb();
  const tx = db.transaction([META_STORE, CHUNK_STORE], "readwrite");
  const metaStore = tx.objectStore(META_STORE);
  const request = metaStore.get(id);
  request.onsuccess = () => {
    if (!request.result) return;
    metaStore.put({ ...request.result, ...metaPatch });
    if (result) tx.objectStore(CHUNK_STORE).put({ id, ...result });
  };
  await done(tx);
}

export async function getProcessing(ids) {
  const db = await openDb();
  const tx = db.transaction(CHUNK_STORE, "readonly");
  const store = tx.objectStore(CHUNK_STORE);
  const requests = ids.map(id => store.get(id));
  await done(tx);
  return requests.map(r => r.result).filter(Boolean);
}

