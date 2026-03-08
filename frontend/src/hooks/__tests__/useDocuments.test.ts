import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useDocuments, PAGE_SIZE, MAX_UPLOAD_BYTES } from "../useDocuments";
import * as documentsApi from "../../api/documents";
import { ApiError } from "../../api/errors";

vi.mock("../../api/documents", async (importOriginal) => {
  const actual = await importOriginal<typeof documentsApi>();
  return {
    ...actual,
    fetchDocuments: vi.fn(),
    uploadDocument: vi.fn(),
    deleteDocument: vi.fn(),
  };
});

const mockFetchDocuments = vi.mocked(documentsApi.fetchDocuments);
const mockUploadDocument = vi.mocked(documentsApi.uploadDocument);
const mockDeleteDocument = vi.mocked(documentsApi.deleteDocument);

beforeEach(() => {
  mockFetchDocuments.mockResolvedValue({ documents: [], total: 0 });
});

describe("useDocuments", () => {
  it("loads documents on mount with correct pagination params", async () => {
    const docs = [
      { id: "1", filename: "a.md", content_type: "text/markdown", file_size: 100, chunk_count: 1, created_at: "" },
    ];
    mockFetchDocuments.mockResolvedValue({ documents: docs, total: 1 });

    const { result } = renderHook(() => useDocuments());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(mockFetchDocuments).toHaveBeenCalledWith(PAGE_SIZE, 0);
    expect(result.current.documents).toEqual(docs);
    expect(result.current.total).toBe(1);
    expect(result.current.page).toBe(1);
    expect(result.current.error).toBeNull();
  });

  it("computes totalPages from total count", async () => {
    mockFetchDocuments.mockResolvedValue({ documents: [], total: 50 });

    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.totalPages).toBe(Math.ceil(50 / PAGE_SIZE));
  });

  it("sets error when fetch fails", async () => {
    mockFetchDocuments.mockRejectedValue(new ApiError(500, "Server down"));

    const { result } = renderHook(() => useDocuments());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe("Server down");
  });

  it("upload rejects unsupported file type", async () => {
    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.loading).toBe(false));

    const file = new File(["x"], "photo.jpg", { type: "image/jpeg" });

    await act(async () => {
      await result.current.upload(file);
    });

    expect(result.current.error).toBe("Unsupported file type. Allowed: .pdf, .txt, .md");
    expect(mockUploadDocument).not.toHaveBeenCalled();
  });

  it("upload rejects oversized file", async () => {
    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.loading).toBe(false));

    const content = new ArrayBuffer(MAX_UPLOAD_BYTES + 1);
    const file = new File([content], "huge.pdf", { type: "application/pdf" });

    await act(async () => {
      await result.current.upload(file);
    });

    expect(result.current.error).toBe("File too large. Maximum size is 50 MB.");
    expect(mockUploadDocument).not.toHaveBeenCalled();
  });

  it("upload rejects empty file", async () => {
    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.loading).toBe(false));

    const file = new File([], "empty.md", { type: "text/markdown" });

    await act(async () => {
      await result.current.upload(file);
    });

    expect(result.current.error).toBe("File is empty");
  });

  it("upload success re-fetches page 1", async () => {
    const newDoc = { id: "2", filename: "new.md", content_type: "text/markdown", file_size: 50, chunk_count: 1, created_at: "" };
    mockUploadDocument.mockResolvedValue(newDoc);
    mockFetchDocuments.mockResolvedValue({ documents: [newDoc], total: 1 });

    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.loading).toBe(false));

    const file = new File(["content"], "new.md", { type: "text/markdown" });

    await act(async () => {
      await result.current.upload(file);
    });

    expect(result.current.documents).toEqual([newDoc]);
    expect(result.current.uploading).toBe(false);
  });

  it("upload error sets error state", async () => {
    mockUploadDocument.mockRejectedValue(new ApiError(413, "Too large"));

    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.loading).toBe(false));

    const file = new File(["x"], "big.pdf", { type: "application/pdf" });

    await act(async () => {
      await result.current.upload(file);
    });

    expect(result.current.error).toBe("Too large");
  });

  it("remove deletes and re-fetches current page", async () => {
    const docs = [
      { id: "1", filename: "a.md", content_type: "text/markdown", file_size: 100, chunk_count: 1, created_at: "" },
      { id: "2", filename: "b.md", content_type: "text/markdown", file_size: 200, chunk_count: 2, created_at: "" },
    ];
    mockFetchDocuments.mockResolvedValue({ documents: docs, total: 2 });
    mockDeleteDocument.mockResolvedValue(undefined);

    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.loading).toBe(false));

    const remaining = [docs[1]];
    mockFetchDocuments.mockResolvedValue({ documents: remaining, total: 1 });

    await act(async () => {
      await result.current.remove("1");
    });

    expect(mockDeleteDocument).toHaveBeenCalledWith("1");
    expect(result.current.documents).toEqual(remaining);
  });

  it("remove error sets error state", async () => {
    mockDeleteDocument.mockRejectedValue(new ApiError(404, "Not found"));

    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.remove("missing");
    });

    expect(result.current.error).toBe("Not found");
  });

  it("clearError resets error to null", async () => {
    mockFetchDocuments.mockRejectedValue(new Error("fail"));

    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.error).not.toBeNull());

    act(() => {
      result.current.clearError();
    });

    expect(result.current.error).toBeNull();
  });
});
