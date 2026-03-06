import { useCallback, useEffect, useState } from "react";
import {
  type DocumentResponse,
  deleteDocument,
  fetchDocuments,
  isAllowedFileType,
  uploadDocument,
} from "../api/documents.ts";
import { ApiError } from "../api/errors.ts";

interface UseDocumentsReturn {
  documents: DocumentResponse[];
  loading: boolean;
  error: string | null;
  uploading: boolean;
  upload: (file: File) => Promise<void>;
  remove: (id: string) => Promise<void>;
  clearError: () => void;
}

export function useDocuments(): UseDocumentsReturn {
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDocuments = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchDocuments();
      setDocuments(data.documents);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

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
      const doc = await uploadDocument(file);
      setDocuments((prev) => [doc, ...prev]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to upload document");
    } finally {
      setUploading(false);
    }
  }, []);

  const remove = useCallback(async (id: string) => {
    try {
      setError(null);
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete document");
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return { documents, loading, error, uploading, upload, remove, clearError };
}
