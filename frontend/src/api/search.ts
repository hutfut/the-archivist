import { throwIfNotOk } from "./errors";

export interface SearchResult {
  document_id: string;
  filename: string;
  title: string;
  section_heading: string | null;
  snippet: string;
  score: number;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  query: string;
}

export async function searchDocuments(
  query: string,
  limit = 10,
  offset = 0,
): Promise<SearchResponse> {
  const params = new URLSearchParams({
    q: query,
    limit: String(limit),
    offset: String(offset),
  });
  const response = await fetch(`/api/search?${params}`);
  await throwIfNotOk(response);
  return response.json();
}
