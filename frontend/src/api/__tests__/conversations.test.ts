import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  createConversation,
  fetchConversations,
  fetchConversation,
  deleteConversation,
  sendMessageStream,
  type StreamCallbacks,
} from "../conversations";
import { ApiError } from "../errors";

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

describe("createConversation", () => {
  it("sends POST and returns conversation", async () => {
    const conv = { id: "c1", title: null, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" };
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(conv), { status: 201 }),
    );

    const result = await createConversation();
    expect(result).toEqual(conv);
    expect(fetch).toHaveBeenCalledWith("/api/conversations", { method: "POST" });
  });
});

describe("fetchConversations", () => {
  it("returns conversation list", async () => {
    const payload = { conversations: [{ id: "c1", title: "Chat", created_at: "", updated_at: "" }] };
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(payload), { status: 200 }),
    );

    const result = await fetchConversations();
    expect(result).toEqual(payload);
    expect(fetch).toHaveBeenCalledWith("/api/conversations");
  });
});

describe("fetchConversation", () => {
  it("returns conversation detail with messages", async () => {
    const detail = {
      id: "c1",
      title: "Chat",
      created_at: "",
      updated_at: "",
      messages: [{ id: "m1", conversation_id: "c1", role: "user", content: "hi", sources: null, created_at: "" }],
    };
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify(detail), { status: 200 }),
    );

    const result = await fetchConversation("c1");
    expect(result).toEqual(detail);
    expect(fetch).toHaveBeenCalledWith("/api/conversations/c1");
  });

  it("encodes ID in URL", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({}), { status: 200 }),
    );

    await fetchConversation("id/special");
    expect(fetch).toHaveBeenCalledWith("/api/conversations/id%2Fspecial");
  });
});

describe("deleteConversation", () => {
  it("sends DELETE with encoded ID", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(null, { status: 204 }));

    await deleteConversation("c1");
    expect(fetch).toHaveBeenCalledWith("/api/conversations/c1", { method: "DELETE" });
  });

  it("throws ApiError on failure", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: "Not found" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(deleteConversation("missing")).rejects.toThrow(ApiError);
  });
});

describe("sendMessageStream", () => {
  function createSSEStream(events: string[]): ReadableStream<Uint8Array> {
    const encoder = new TextEncoder();
    const text = events.join("\n") + "\n";
    return new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(text));
        controller.close();
      },
    });
  }

  function makeCallbacks(): StreamCallbacks & {
    calls: Array<{ type: string; args: unknown[] }>;
  } {
    const calls: Array<{ type: string; args: unknown[] }> = [];
    return {
      calls,
      onStart: (id) => calls.push({ type: "onStart", args: [id] }),
      onDelta: (delta) => calls.push({ type: "onDelta", args: [delta] }),
      onSources: (sources) => calls.push({ type: "onSources", args: [sources] }),
      onEnd: (id) => calls.push({ type: "onEnd", args: [id] }),
      onError: (err) => calls.push({ type: "onError", args: [err] }),
    };
  }

  it("fires callbacks in order for a complete SSE stream", async () => {
    const stream = createSSEStream([
      'event: message_start',
      'data: {"message_id":"m1"}',
      '',
      'event: content_delta',
      'data: {"delta":"Hello"}',
      '',
      'event: content_delta',
      'data: {"delta":" world"}',
      '',
      'event: sources',
      'data: {"sources":[{"document_id":"d1","filename":"f.md","chunk_content":"c","similarity_score":0.9,"section_heading":null}]}',
      '',
      'event: message_end',
      'data: {"message_id":"m1"}',
    ]);

    vi.mocked(fetch).mockResolvedValue(
      new Response(stream, { status: 200 }),
    );

    const cb = makeCallbacks();
    sendMessageStream("c1", "hi", cb);

    await vi.waitFor(() => {
      expect(cb.calls.some((c) => c.type === "onEnd")).toBe(true);
    });

    const types = cb.calls.map((c) => c.type);
    expect(types).toEqual(["onStart", "onDelta", "onDelta", "onSources", "onEnd"]);
    expect(cb.calls[0].args).toEqual(["m1"]);
    expect(cb.calls[1].args).toEqual(["Hello"]);
    expect(cb.calls[2].args).toEqual([" world"]);
    expect(cb.calls[4].args).toEqual(["m1"]);
  });

  it("fires onError for SSE error events", async () => {
    const stream = createSSEStream([
      'event: message_start',
      'data: {"message_id":"m1"}',
      '',
      'event: error',
      'data: {"detail":"Something broke"}',
    ]);

    vi.mocked(fetch).mockResolvedValue(
      new Response(stream, { status: 200 }),
    );

    const cb = makeCallbacks();
    sendMessageStream("c1", "hi", cb);

    await vi.waitFor(() => {
      expect(cb.calls.some((c) => c.type === "onError")).toBe(true);
    });

    const errorCall = cb.calls.find((c) => c.type === "onError");
    expect(errorCall?.args[0]).toBeInstanceOf(ApiError);
    expect((errorCall?.args[0] as ApiError).message).toBe("Something broke");
  });

  it("fires onError for non-ok response", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response("error", { status: 500, statusText: "Internal Server Error" }),
    );

    const cb = makeCallbacks();
    sendMessageStream("c1", "hi", cb);

    await vi.waitFor(() => {
      expect(cb.calls.some((c) => c.type === "onError")).toBe(true);
    });

    const errorCall = cb.calls.find((c) => c.type === "onError");
    expect(errorCall?.args[0]).toBeInstanceOf(ApiError);
    expect((errorCall?.args[0] as ApiError).status).toBe(500);
  });

  it("sends POST with correct URL, headers, and body", async () => {
    const stream = createSSEStream([
      'event: message_start',
      'data: {"message_id":"m1"}',
      '',
      'event: message_end',
      'data: {"message_id":"m1"}',
    ]);

    vi.mocked(fetch).mockResolvedValue(
      new Response(stream, { status: 200 }),
    );

    const cb = makeCallbacks();
    sendMessageStream("conv-id", "hello", cb);

    await vi.waitFor(() => {
      expect(cb.calls.some((c) => c.type === "onEnd")).toBe(true);
    });

    const [url, options] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("/api/conversations/conv-id/messages/stream");
    expect(options?.method).toBe("POST");
    expect(options?.headers).toEqual({ "Content-Type": "application/json" });
    expect(JSON.parse(options?.body as string)).toEqual({ content: "hello" });
  });

  it("returns an AbortController", () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(createSSEStream([]), { status: 200 }),
    );

    const cb = makeCallbacks();
    const controller = sendMessageStream("c1", "hi", cb);
    expect(controller).toBeInstanceOf(AbortController);
  });

  it("does not fire onError when aborted", async () => {
    let resolveReader!: () => void;
    const neverResolve = new Promise<void>((r) => { resolveReader = r; });

    const stream = new ReadableStream({
      async pull(controller) {
        await neverResolve;
        controller.close();
      },
    });

    vi.mocked(fetch).mockResolvedValue(
      new Response(stream, { status: 200 }),
    );

    const cb = makeCallbacks();
    const controller = sendMessageStream("c1", "hi", cb);

    await new Promise((r) => setTimeout(r, 50));
    controller.abort();
    resolveReader();
    await new Promise((r) => setTimeout(r, 50));

    expect(cb.calls.filter((c) => c.type === "onError")).toHaveLength(0);
  });
});
