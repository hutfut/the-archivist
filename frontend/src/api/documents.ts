import { throwIfNotOk } from "./errors";

export interface DocumentResponse {
  id: string;
  filename: string;
  content_type: string;
  file_size: number;
  chunk_count: number;
  created_at: string;
}

export interface DocumentListResponse {
  documents: DocumentResponse[];
  total: number;
}

const ALLOWED_EXTENSIONS = new Set([".pdf", ".txt", ".md"]);

export function getFileExtension(filename: string): string {
  const dot = filename.lastIndexOf(".");
  return dot === -1 ? "" : filename.slice(dot).toLowerCase();
}

export function isAllowedFileType(filename: string): boolean {
  return ALLOWED_EXTENSIONS.has(getFileExtension(filename));
}

export async function fetchDocuments(
  limit: number,
  offset: number,
): Promise<DocumentListResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  const response = await fetch(`/api/documents?${params}`);
  await throwIfNotOk(response);
  return response.json();
}

export async function uploadDocument(file: File): Promise<DocumentResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch("/api/documents", {
    method: "POST",
    body: formData,
  });
  await throwIfNotOk(response);
  return response.json();
}

export async function deleteDocument(id: string): Promise<void> {
  const response = await fetch(`/api/documents/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
  await throwIfNotOk(response);
}
