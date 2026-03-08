import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useChat } from "../useChat";
import * as conversationsApi from "../../api/conversations";
import { ApiError } from "../../api/errors";

vi.mock("../../api/conversations", async (importOriginal) => {
  const actual = await importOriginal<typeof conversationsApi>();
  return {
    ...actual,
    fetchConversations: vi.fn(),
    createConversation: vi.fn(),
    fetchConversation: vi.fn(),
    deleteConversation: vi.fn(),
    sendMessageStream: vi.fn(),
  };
});

const mockFetchConversations = vi.mocked(conversationsApi.fetchConversations);
const mockCreateConversation = vi.mocked(conversationsApi.createConversation);
const mockFetchConversation = vi.mocked(conversationsApi.fetchConversation);
const mockDeleteConversation = vi.mocked(conversationsApi.deleteConversation);
const mockSendMessageStream = vi.mocked(conversationsApi.sendMessageStream);

const makeConv = (id: string, title: string | null = null): conversationsApi.ConversationResponse => ({
  id,
  title,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
});

beforeEach(() => {
  mockFetchConversations.mockResolvedValue({ conversations: [] });
});

describe("useChat", () => {
  it("loads conversations on mount", async () => {
    const convs = [makeConv("c1", "Chat 1")];
    mockFetchConversations.mockResolvedValue({ conversations: convs });

    const { result } = renderHook(() => useChat());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.conversations).toEqual(convs);
  });

  it("sets error when loading conversations fails", async () => {
    mockFetchConversations.mockRejectedValue(new ApiError(500, "Down"));

    const { result } = renderHook(() => useChat());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe("Down");
  });

  it("createChat creates and activates conversation", async () => {
    const newConv = makeConv("c-new", null);
    mockCreateConversation.mockResolvedValue(newConv);

    const { result } = renderHook(() => useChat());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.createChat();
    });

    expect(result.current.conversations[0]).toEqual(newConv);
    expect(result.current.activeConversationId).toBe("c-new");
    expect(result.current.messages).toEqual([]);
  });

  it("selectConversation fetches and sets messages", async () => {
    const msgs = [
      { id: "m1", conversation_id: "c1", role: "user" as const, content: "hi", sources: null, created_at: "" },
    ];
    mockFetchConversation.mockResolvedValue({
      ...makeConv("c1"),
      messages: msgs,
    });

    const { result } = renderHook(() => useChat());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.selectConversation("c1");
    });

    expect(result.current.activeConversationId).toBe("c1");
    expect(result.current.messages).toEqual(msgs);
  });

  it("selectConversation sets error on failure", async () => {
    mockFetchConversation.mockRejectedValue(new ApiError(404, "Gone"));

    const { result } = renderHook(() => useChat());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.selectConversation("c1");
    });

    expect(result.current.error).toBe("Gone");
  });

  it("deleteChat removes conversation and switches active", async () => {
    const convs = [makeConv("c1", "A"), makeConv("c2", "B")];
    mockFetchConversations.mockResolvedValue({ conversations: convs });
    mockDeleteConversation.mockResolvedValue(undefined);
    mockFetchConversation.mockResolvedValue({ ...makeConv("c2"), messages: [] });

    const { result } = renderHook(() => useChat());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.selectConversation("c1");
    });

    await act(async () => {
      await result.current.deleteChat("c1");
    });

    expect(result.current.conversations).toHaveLength(1);
    expect(result.current.conversations[0].id).toBe("c2");
    expect(result.current.activeConversationId).toBe("c2");
  });

  it("deleteChat sets error on failure", async () => {
    mockDeleteConversation.mockRejectedValue(new ApiError(500, "Delete failed"));

    const { result } = renderHook(() => useChat());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.deleteChat("c1");
    });

    expect(result.current.error).toBe("Delete failed");
  });

  it("sendMessage no-ops when no active conversation", async () => {
    const { result } = renderHook(() => useChat());
    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.sendMessage("hello");
    });

    expect(mockSendMessageStream).not.toHaveBeenCalled();
  });

  it("sendMessage adds optimistic user message and calls stream", async () => {
    const convs = [makeConv("c1")];
    mockFetchConversations.mockResolvedValue({ conversations: convs });
    mockFetchConversation.mockResolvedValue({ ...makeConv("c1"), messages: [] });
    mockSendMessageStream.mockReturnValue(new AbortController());

    const { result } = renderHook(() => useChat());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.selectConversation("c1");
    });

    act(() => {
      result.current.sendMessage("hello");
    });

    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].role).toBe("user");
    expect(result.current.messages[0].content).toBe("hello");
    expect(result.current.sending).toBe(true);
    expect(result.current.streaming).toEqual({ content: "", sources: [] });
    expect(mockSendMessageStream).toHaveBeenCalledWith(
      "c1",
      "hello",
      expect.objectContaining({
        onStart: expect.any(Function),
        onDelta: expect.any(Function),
        onSources: expect.any(Function),
        onEnd: expect.any(Function),
        onError: expect.any(Function),
      }),
    );
  });

  it("sendMessage no-ops when already sending", async () => {
    mockFetchConversations.mockResolvedValue({ conversations: [makeConv("c1")] });
    mockFetchConversation.mockResolvedValue({ ...makeConv("c1"), messages: [] });
    mockSendMessageStream.mockReturnValue(new AbortController());

    const { result } = renderHook(() => useChat());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.selectConversation("c1");
    });

    // Two rapid sends in the same tick — only the first should go through
    act(() => {
      result.current.sendMessage("first");
      result.current.sendMessage("second");
    });

    expect(mockSendMessageStream).toHaveBeenCalledTimes(1);
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].content).toBe("first");
  });

  it("clearError resets error to null", async () => {
    mockFetchConversations.mockRejectedValue(new Error("fail"));

    const { result } = renderHook(() => useChat());
    await waitFor(() => expect(result.current.error).not.toBeNull());

    act(() => {
      result.current.clearError();
    });

    expect(result.current.error).toBeNull();
  });
});
