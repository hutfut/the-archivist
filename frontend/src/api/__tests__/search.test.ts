import { describe, it, expect, vi, beforeEach } from "vitest";
import { searchDocuments } from "../search";
import { ApiError } from "../errors";

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

describe("searchDocuments", () => {
  it("constructs query params with defaults", async () => {
    const payload = { results: [], total: 0, query: "test" };
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(payload), { status: 200 }),
    );

    await searchDocuments("test");

    const url = vi.mocked(fetch).mock.calls[0][0] as string;
    const params = new URLSearchParams(url.split("?")[1]);
    expect(params.get("q")).toBe("test");
    expect(params.get("limit")).toBe("10");
    expect(params.get("offset")).toBe("0");
  });

  it("accepts custom limit and offset", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ results: [], total: 0, query: "q" }), {
        status: 200,
      }),
    );

    await searchDocuments("q", 20, 5);

    const url = vi.mocked(fetch).mock.calls[0][0] as string;
    const params = new URLSearchParams(url.split("?")[1]);
    expect(params.get("limit")).toBe("20");
    expect(params.get("offset")).toBe("5");
  });

  it("returns parsed search results", async () => {
    const payload = {
      results: [
        {
          document_id: "d1",
          filename: "doc.md",
          title: "Doc",
          section_heading: null,
          snippet: "found it",
          score: 0.9,
        },
      ],
      total: 1,
      query: "search",
    };
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(payload), { status: 200 }),
    );

    const result = await searchDocuments("search");
    expect(result).toEqual(payload);
  });

  it("throws ApiError on failure", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: "Bad query" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(searchDocuments("")).rejects.toThrow(ApiError);
  });
});
