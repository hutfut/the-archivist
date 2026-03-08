import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getFileExtension,
  isAllowedFileType,
  fetchDocuments,
  uploadDocument,
  deleteDocument,
} from "../documents";
import { ApiError } from "../errors";

describe("getFileExtension", () => {
  it("extracts .pdf extension", () => {
    expect(getFileExtension("report.pdf")).toBe(".pdf");
  });

  it("lowercases the extension", () => {
    expect(getFileExtension("README.MD")).toBe(".md");
  });

  it("returns empty string for files without extension", () => {
    expect(getFileExtension("Makefile")).toBe("");
  });

  it("extracts only the last extension for multiple dots", () => {
    expect(getFileExtension("archive.tar.gz")).toBe(".gz");
  });
});

describe("isAllowedFileType", () => {
  it.each([".pdf", ".txt", ".md"])("allows %s files", (ext) => {
    expect(isAllowedFileType(`document${ext}`)).toBe(true);
  });

  it("is case insensitive via getFileExtension", () => {
    expect(isAllowedFileType("README.MD")).toBe(true);
    expect(isAllowedFileType("FILE.TXT")).toBe(true);
    expect(isAllowedFileType("doc.PDF")).toBe(true);
  });

  it("rejects .docx files", () => {
    expect(isAllowedFileType("doc.docx")).toBe(false);
  });

  it("rejects .jpg files", () => {
    expect(isAllowedFileType("photo.jpg")).toBe(false);
  });

  it("rejects files without extension", () => {
    expect(isAllowedFileType("Makefile")).toBe(false);
  });
});

describe("fetchDocuments", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("returns parsed document list on success", async () => {
    const payload = { documents: [{ id: "1", filename: "test.md" }] };
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(payload), { status: 200 }),
    );

    const result = await fetchDocuments();
    expect(result).toEqual(payload);
    expect(fetch).toHaveBeenCalledWith("/api/documents");
  });

  it("throws ApiError on failure", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: "Server error" }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(fetchDocuments()).rejects.toThrow(ApiError);
  });
});

describe("uploadDocument", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("sends FormData with the file and returns document", async () => {
    const doc = { id: "2", filename: "upload.pdf" };
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(doc), { status: 201 }),
    );

    const file = new File(["content"], "upload.pdf", { type: "application/pdf" });
    const result = await uploadDocument(file);

    expect(result).toEqual(doc);
    const [url, options] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("/api/documents");
    expect(options?.method).toBe("POST");
    expect(options?.body).toBeInstanceOf(FormData);
  });

  it("throws ApiError on failure", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: "Too large" }), {
        status: 413,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const file = new File(["x"], "big.pdf", { type: "application/pdf" });
    await expect(uploadDocument(file)).rejects.toThrow(ApiError);
  });
});

describe("deleteDocument", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("sends DELETE request with encoded ID", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 204 }));

    await deleteDocument("doc-id/special");
    const [url, options] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("/api/documents/doc-id%2Fspecial");
    expect(options?.method).toBe("DELETE");
  });

  it("throws ApiError on failure", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: "Not found" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(deleteDocument("missing")).rejects.toThrow(ApiError);
  });
});
