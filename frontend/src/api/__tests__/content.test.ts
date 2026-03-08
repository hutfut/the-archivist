import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchDocumentContent, fetchRelatedDocuments } from "../content";
import { ApiError } from "../errors";

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

describe("fetchDocumentContent", () => {
  it("returns parsed content on success", async () => {
    const payload = {
      id: "doc-1",
      filename: "test.md",
      title: "Test",
      content: "# Hello",
      content_type: "text/markdown",
      chunk_count: 3,
      created_at: "2026-01-01T00:00:00Z",
      file_size: 1024,
    };
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(payload), { status: 200 }),
    );

    const result = await fetchDocumentContent("doc-1");
    expect(result).toEqual(payload);
    expect(fetch).toHaveBeenCalledWith("/api/documents/doc-1/content");
  });

  it("encodes the document ID in the URL", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({}), { status: 200 }),
    );

    await fetchDocumentContent("id/with spaces");
    expect(fetch).toHaveBeenCalledWith(
      "/api/documents/id%2Fwith%20spaces/content",
    );
  });

  it("throws ApiError on failure", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: "Not found" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(fetchDocumentContent("missing")).rejects.toThrow(ApiError);
  });
});

describe("fetchRelatedDocuments", () => {
  it("uses default limit of 5", async () => {
    const payload = { documents: [] };
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(payload), { status: 200 }),
    );

    await fetchRelatedDocuments("doc-1");
    expect(fetch).toHaveBeenCalledWith("/api/documents/doc-1/related?limit=5");
  });

  it("passes custom limit", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ documents: [] }), { status: 200 }),
    );

    await fetchRelatedDocuments("doc-1", 10);
    expect(fetch).toHaveBeenCalledWith(
      "/api/documents/doc-1/related?limit=10",
    );
  });

  it("returns parsed related documents on success", async () => {
    const payload = {
      documents: [
        { id: "r1", filename: "related.md", title: "Related", score: 0.85 },
      ],
    };
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(payload), { status: 200 }),
    );

    const result = await fetchRelatedDocuments("doc-1");
    expect(result).toEqual(payload);
  });

  it("throws ApiError on failure", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: "Error" }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(fetchRelatedDocuments("doc-1")).rejects.toThrow(ApiError);
  });
});
