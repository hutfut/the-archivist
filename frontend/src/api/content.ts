import { throwIfNotOk } from "./errors";

export interface DocumentContent {
  id: string;
  filename: string;
  title: string;
  content: string;
  content_type: string;
  chunk_count: number;
  created_at: string;
  file_size: number;
}

export interface RelatedDocument {
  id: string;
  filename: string;
  title: string;
  score: number;
}

export interface RelatedDocumentsResponse {
  documents: RelatedDocument[];
}

export async function fetchDocumentContent(
  documentId: string,
): Promise<DocumentContent> {
  const response = await fetch(
    `/api/documents/${encodeURIComponent(documentId)}/content`,
  );
  await throwIfNotOk(response);
  return response.json();
}

export async function fetchRelatedDocuments(
  documentId: string,
  limit = 5,
): Promise<RelatedDocumentsResponse> {
  const response = await fetch(
    `/api/documents/${encodeURIComponent(documentId)}/related?limit=${limit}`,
  );
  await throwIfNotOk(response);
  return response.json();
}
