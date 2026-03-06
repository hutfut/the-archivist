import { useCallback, useEffect, useRef, useState } from "react";
import {
  type ConversationResponse,
  type MessageResponse,
  type SourceAttribution,
  createConversation,
  deleteConversation,
  fetchConversation,
  fetchConversations,
  sendMessageStream,
} from "../api/conversations.ts";
import { ApiError } from "../api/errors.ts";

export interface StreamingMessage {
  content: string;
  sources: SourceAttribution[];
}

export interface UseChatReturn {
  conversations: ConversationResponse[];
  activeConversationId: string | null;
  messages: MessageResponse[];
  sending: boolean;
  streaming: StreamingMessage | null;
  loading: boolean;
  error: string | null;
  createChat: () => Promise<void>;
  selectConversation: (id: string) => Promise<void>;
  deleteChat: (id: string) => Promise<void>;
  sendMessage: (content: string) => void;
  clearError: () => void;
}

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

export function useChat(): UseChatReturn {
  const [conversations, setConversations] = useState<ConversationResponse[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [sending, setSending] = useState(false);
  const [streaming, setStreaming] = useState<StreamingMessage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);

  const loadConversations = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchConversations();
      setConversations(data.conversations);
    } catch (err) {
      setError(errorMessage(err, "Failed to load conversations"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const selectConversation = useCallback(async (id: string) => {
    try {
      setActiveConversationId(id);
      setMessages([]);
      setStreaming(null);
      setError(null);
      const detail = await fetchConversation(id);
      setMessages(detail.messages);
    } catch (err) {
      setError(errorMessage(err, "Failed to load conversation"));
    }
  }, []);

  const createChat = useCallback(async () => {
    try {
      setError(null);
      const conv = await createConversation();
      setConversations((prev) => [conv, ...prev]);
      setActiveConversationId(conv.id);
      setMessages([]);
      setStreaming(null);
    } catch (err) {
      setError(errorMessage(err, "Failed to create conversation"));
    }
  }, []);

  const deleteChat = useCallback(
    async (id: string) => {
      try {
        setError(null);
        await deleteConversation(id);
        setConversations((prev) => {
          const next = prev.filter((c) => c.id !== id);
          if (activeConversationId === id) {
            const nextActive = next.length > 0 ? next[0].id : null;
            setActiveConversationId(nextActive);
            if (nextActive) {
              fetchConversation(nextActive).then((detail) =>
                setMessages(detail.messages),
              );
            } else {
              setMessages([]);
            }
          }
          return next;
        });
      } catch (err) {
        setError(errorMessage(err, "Failed to delete conversation"));
      }
    },
    [activeConversationId],
  );

  const sendMessage = useCallback(
    (content: string) => {
      if (!activeConversationId || sending) return;

      const userMessage: MessageResponse = {
        id: `temp-${Date.now()}`,
        conversation_id: activeConversationId,
        role: "user",
        content,
        sources: null,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setSending(true);
      setStreaming({ content: "", sources: [] });
      setError(null);

      let accumulatedContent = "";
      let accumulatedSources: SourceAttribution[] = [];
      let messageId = "";
      const conversationId = activeConversationId;

      abortRef.current = sendMessageStream(conversationId, content, {
        onStart: (id) => {
          messageId = id;
        },
        onDelta: (delta) => {
          accumulatedContent += delta;
          setStreaming({ content: accumulatedContent, sources: accumulatedSources });
        },
        onSources: (sources) => {
          accumulatedSources = sources;
          setStreaming({ content: accumulatedContent, sources: accumulatedSources });
        },
        onEnd: () => {
          const assistantMessage: MessageResponse = {
            id: messageId,
            conversation_id: conversationId,
            role: "assistant",
            content: accumulatedContent,
            sources: accumulatedSources.length > 0 ? accumulatedSources : null,
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, assistantMessage]);
          setStreaming(null);
          setSending(false);
          abortRef.current = null;

          setConversations((prev) => {
            const idx = prev.findIndex((c) => c.id === conversationId);
            if (idx === -1) return prev;
            const updated = { ...prev[idx], updated_at: new Date().toISOString() };
            if (updated.title === null) {
              updated.title = content.slice(0, 100);
            }
            return [updated, ...prev.filter((c) => c.id !== conversationId)];
          });
        },
        onError: (err) => {
          setStreaming(null);
          setSending(false);
          setError(err.message || "Failed to send message");
          abortRef.current = null;
        },
      });
    },
    [activeConversationId, sending],
  );

  const clearError = useCallback(() => setError(null), []);

  return {
    conversations,
    activeConversationId,
    messages,
    sending,
    streaming,
    loading,
    error,
    createChat,
    selectConversation,
    deleteChat,
    sendMessage,
    clearError,
  };
}
