import { useCallback, useEffect, useState } from "react";
import {
  type DocumentResponse,
  deleteDocument,
  fetchDocuments,
  isAllowedFileType,
  uploadDocument,
} from "../api/documents.ts";
import { ApiError } from "../api/errors.ts";

export const PAGE_SIZE = 24;

export interface UseDocumentsReturn {
  documents: DocumentResponse[];
  total: number;
  page: number;
  totalPages: number;
  setPage: (page: number) => void;
  loading: boolean;
  error: string | null;
  uploading: boolean;
  upload: (file: File) => Promise<void>;
  remove: (id: string) => Promise<void>;
  clearError: () => void;
}

export function useDocuments(): UseDocumentsReturn {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPageRaw] = useState(1);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const setPage = useCallback(
    (p: number) => setPageRaw(Math.max(1, Math.min(p, totalPages))),
    [totalPages],
  );

  const loadDocuments = useCallback(async (p: number) => {
    try {
      setLoading(true);
      const offset = (p - 1) * PAGE_SIZE;
      const data = await fetchDocuments(PAGE_SIZE, offset);
      setDocuments(data.documents);
      setTotal(data.total);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments(page);
  }, [page, loadDocuments]);

  const upload = useCallback(async (file: File) => {
    if (!file.name || !isAllowedFileType(file.name)) {
      setError("Unsupported file type. Allowed: .pdf, .txt, .md");
      return;
    }
    if (file.size === 0) {
      setError("File is empty");
      return;
    }

    try {
      setUploading(true);
      setError(null);
      await uploadDocument(file);
      setPageRaw(1);
      await loadDocuments(1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to upload document");
    } finally {
      setUploading(false);
    }
  }, [loadDocuments]);

  const remove = useCallback(async (id: string) => {
    try {
      setError(null);
      await deleteDocument(id);
      await loadDocuments(page);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete document");
    }
  }, [page, loadDocuments]);

  const clearError = useCallback(() => setError(null), []);

  return {
    documents, total, page, totalPages, setPage,
    loading, error, uploading, upload, remove, clearError,
  };
}
