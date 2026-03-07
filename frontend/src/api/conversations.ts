import { ApiError, throwIfNotOk } from "./errors.ts";

export interface SourceAttribution {
  document_id: string;
  filename: string;
  chunk_content: string;
  similarity_score: number;
  section_heading: string | null;
}

export interface MessageResponse {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  sources: SourceAttribution[] | null;
  created_at: string;
}

export interface ConversationResponse {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationListResponse {
  conversations: ConversationResponse[];
}

export interface ConversationDetailResponse extends ConversationResponse {
  messages: MessageResponse[];
}

export async function createConversation(): Promise<ConversationResponse> {
  const response = await fetch("/api/conversations", { method: "POST" });
  await throwIfNotOk(response);
  return response.json();
}

export async function fetchConversations(): Promise<ConversationListResponse> {
  const response = await fetch("/api/conversations");
  await throwIfNotOk(response);
  return response.json();
}

export async function fetchConversation(
  id: string,
): Promise<ConversationDetailResponse> {
  const response = await fetch(
    `/api/conversations/${encodeURIComponent(id)}`,
  );
  await throwIfNotOk(response);
  return response.json();
}

export async function deleteConversation(id: string): Promise<void> {
  const response = await fetch(
    `/api/conversations/${encodeURIComponent(id)}`,
    { method: "DELETE" },
  );
  await throwIfNotOk(response);
}

export interface StreamCallbacks {
  onStart: (messageId: string) => void;
  onDelta: (delta: string) => void;
  onSources: (sources: SourceAttribution[]) => void;
  onEnd: (messageId: string) => void;
  onError: (error: Error) => void;
}

/**
 * Send a message and consume the SSE stream of the assistant's response.
 * Returns an AbortController so the caller can cancel the stream.
 */
export function sendMessageStream(
  conversationId: string,
  content: string,
  callbacks: StreamCallbacks,
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const response = await fetch(
        `/api/conversations/${encodeURIComponent(conversationId)}/messages/stream`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content }),
          signal: controller.signal,
        },
      );

      if (!response.ok) {
        const message = response.statusText || `Request failed (${response.status})`;
        throw new ApiError(response.status, message);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("Response body is not readable");
      }

      const decoder = new TextDecoder();
      let buffer = "";

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        let currentEvent: string | null = null;
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7);
          } else if (line.startsWith("data: ") && currentEvent !== null) {
            const data = JSON.parse(line.slice(6));
            switch (currentEvent) {
              case "message_start":
                callbacks.onStart(data.message_id);
                break;
              case "content_delta":
                callbacks.onDelta(data.delta);
                break;
              case "sources":
                callbacks.onSources(data.sources ?? []);
                break;
              case "message_end":
                callbacks.onEnd(data.message_id);
                break;
              case "error":
                callbacks.onError(new ApiError(0, data.detail));
                break;
            }
            currentEvent = null;
          }
        }
      }
    } catch (err) {
      if ((err as DOMException).name === "AbortError") return;
      callbacks.onError(
        err instanceof Error ? err : new Error(String(err)),
      );
    }
  })();

  return controller;
}
