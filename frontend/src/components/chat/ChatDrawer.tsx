import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { Link } from "react-router-dom";
import Markdown from "react-markdown";
import type {
  ConversationResponse,
  MessageResponse,
  SourceAttribution,
} from "../../api/conversations";
import type { StreamingMessage, UseChatReturn } from "../../hooks/useChat";
import { toSlug } from "../../lib/utils";

interface ChatDrawerProps {
  open: boolean;
  onClose: () => void;
  chat: UseChatReturn;
  prefill?: string;
  onPrefillConsumed: () => void;
}

export function ChatDrawer({
  open,
  onClose,
  chat,
  prefill,
  onPrefillConsumed,
}: ChatDrawerProps) {
  const {
    conversations,
    activeConversationId,
    messages,
    sending,
    streaming,
    error,
    createChat,
    selectConversation,
    deleteChat,
    sendMessage,
    clearError,
  } = chat;

  const prefillSentRef = useRef(false);

  useEffect(() => {
    if (!open || !prefill || prefillSentRef.current) return;

    if (activeConversationId) {
      prefillSentRef.current = true;
      sendMessage(prefill);
      onPrefillConsumed();
    } else {
      createChat();
    }
  }, [open, prefill, activeConversationId, sendMessage, onPrefillConsumed, createChat]);

  useEffect(() => {
    if (!open) {
      prefillSentRef.current = false;
    }
  }, [open]);

  useEffect(() => {
    function handleEsc(e: globalThis.KeyboardEvent) {
      if (e.key === "Escape" && open) {
        onClose();
      }
    }
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [open, onClose]);

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 bg-black/40 z-40 transition-opacity"
          onClick={onClose}
        />
      )}

      <div
        className={`fixed top-0 right-0 h-full w-full sm:w-[420px] bg-[var(--color-bg-secondary)] border-l border-[var(--color-border)] shadow-2xl z-50 flex flex-col transform transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[var(--color-accent-gold)] to-[var(--color-accent-crimson)] flex items-center justify-center">
              <span className="text-sm font-bold text-[var(--color-bg-primary)]">A</span>
            </div>
            <div>
              <h3 className="text-sm font-heading font-semibold text-[var(--color-accent-gold)]">
                The Archivist
              </h3>
              <p className="text-xs text-[var(--color-text-muted)]">
                AI Document Assistant
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-md text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-hover)] transition-colors cursor-pointer"
            title="Close chat (Esc)"
          >
            <CloseIcon />
          </button>
        </div>

        <ConversationBar
          conversations={conversations}
          activeId={activeConversationId}
          onSelect={selectConversation}
          onCreate={createChat}
          onDelete={deleteChat}
        />

        {error && (
          <div className="mx-3 mt-2 p-2 rounded-md bg-[var(--color-accent-crimson-dim)]/30 text-xs text-red-300 flex items-start gap-2">
            <span className="flex-1">{error}</span>
            <button type="button" onClick={clearError} className="text-red-400 hover:text-red-200 cursor-pointer">&times;</button>
          </div>
        )}

        {activeConversationId ? (
          <>
            <MessageList messages={messages} streaming={streaming} />
            <MessageInput onSend={sendMessage} disabled={sending} />
          </>
        ) : (
          <DrawerEmptyState onCreate={createChat} />
        )}
      </div>
    </>
  );
}

function ConversationBar({
  conversations,
  activeId,
  onSelect,
  onCreate,
  onDelete,
}: {
  conversations: ConversationResponse[];
  activeId: string | null;
  onSelect: (id: string) => Promise<void>;
  onCreate: () => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 border-b border-[var(--color-border)] shrink-0">
      <select
        value={activeId ?? ""}
        onChange={(e) => {
          if (e.target.value) onSelect(e.target.value);
        }}
        className="poe-input flex-1 min-w-0 py-1.5 text-xs truncate"
      >
        {conversations.length === 0 && <option value="">No conversations</option>}
        {conversations.map((c) => (
          <option key={c.id} value={c.id}>
            {c.title ?? "New conversation"}
          </option>
        ))}
      </select>
      <button type="button" onClick={onCreate} title="New conversation" className="p-1.5 rounded-md text-[var(--color-text-secondary)] hover:text-[var(--color-accent-gold)] hover:bg-[var(--color-surface-hover)] transition-colors cursor-pointer">
        <PlusIcon />
      </button>
      {activeId && (
        <button type="button" onClick={() => onDelete(activeId)} title="Delete conversation" className="p-1.5 rounded-md text-[var(--color-text-muted)] hover:text-red-400 hover:bg-red-950/30 transition-colors cursor-pointer">
          <TrashIcon />
        </button>
      )}
    </div>
  );
}

function MessageList({
  messages,
  streaming,
}: {
  messages: MessageResponse[];
  streaming: StreamingMessage | null;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming?.content]);

  if (messages.length === 0 && !streaming) {
    return (
      <div className="flex-1 flex items-center justify-center text-[var(--color-text-muted)] text-sm px-6 text-center">
        Send a message to start the conversation.
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      {streaming && (
        <div className="flex justify-start">
          <div className="max-w-[90%] rounded-lg px-3 py-2 bg-[var(--color-bg-tertiary)] border border-[var(--color-border-gold)] text-[var(--color-text-primary)]">
            {streaming.content ? (
              <div className="prose prose-sm prose-invert max-w-none text-[var(--color-text-primary)] text-sm [&_a]:text-[var(--color-accent-blue)]">
                <Markdown>{streaming.content}</Markdown>
              </div>
            ) : (
              <TypingIndicator />
            )}
            {streaming.sources.length > 0 && (
              <SourcesDisplay sources={streaming.sources} />
            )}
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}

function MessageBubble({ message }: { message: MessageResponse }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[90%] rounded-lg px-3 py-2 text-sm ${
          isUser
            ? "bg-[var(--color-accent-gold-dim)] text-[var(--color-text-heading)]"
            : "bg-[var(--color-bg-tertiary)] border border-[var(--color-border-gold)] text-[var(--color-text-primary)]"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose prose-sm prose-invert max-w-none text-[var(--color-text-primary)] [&_a]:text-[var(--color-accent-blue)]">
            <Markdown>{message.content}</Markdown>
          </div>
        )}
        {!isUser && message.sources && message.sources.length > 0 && (
          <SourcesDisplay sources={message.sources} />
        )}
      </div>
    </div>
  );
}

function SourcesDisplay({ sources }: { sources: SourceAttribution[] }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mt-2 pt-2 border-t border-[var(--color-border)]">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="text-xs font-medium text-[var(--color-accent-gold-dim)] hover:text-[var(--color-accent-gold)] cursor-pointer"
      >
        Sources ({sources.length})
      </button>
      {expanded && (
        <ul className="mt-1.5 space-y-1.5">
          {sources.map((source, i) => (
            <li key={`${source.document_id}-${i}`} className="text-xs">
              <Link
                to={`/doc/${toSlug(source.document_id, source.filename)}`}
                className="font-medium text-[var(--color-accent-blue)] hover:underline"
              >
                {source.section_heading
                  ? `${source.filename} > ${source.section_heading}`
                  : source.filename}
              </Link>
              <span className="text-[var(--color-text-muted)] ml-1">
                ({(source.similarity_score * 100).toFixed(0)}%)
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function MessageInput({
  onSend,
  disabled,
}: {
  onSend: (content: string) => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const submit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }, [value, disabled, onSend]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    submit();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="shrink-0 flex items-end gap-2 px-3 py-3 border-t border-[var(--color-border)]"
    >
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        placeholder="Ask about your documents..."
        disabled={disabled}
        rows={1}
        className="poe-input flex-1 resize-none py-2 text-sm"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="poe-btn-primary px-3 py-2 disabled:opacity-40"
        title="Send"
      >
        <SendIcon />
      </button>
    </form>
  );
}

function DrawerEmptyState({ onCreate }: { onCreate: () => Promise<void> }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center px-6 gap-4">
      <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[var(--color-accent-gold)]/20 to-[var(--color-accent-crimson)]/10 border border-[var(--color-border-gold)] flex items-center justify-center">
        <span className="text-2xl font-heading text-[var(--color-accent-gold)]">A</span>
      </div>
      <div>
        <h3 className="font-heading text-base font-semibold text-[var(--color-accent-gold)]">
          The Archivist
        </h3>
        <p className="text-sm text-[var(--color-text-secondary)] mt-1">
          I am The Archivist. Ask me anything about your uploaded documents...
        </p>
      </div>
      <button type="button" onClick={onCreate} className="poe-btn-primary text-sm">
        New Conversation
      </button>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-1 py-1" aria-label="Assistant is typing">
      <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent-gold)] animate-bounce [animation-delay:0ms]" />
      <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent-gold)] animate-bounce [animation-delay:150ms]" />
      <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent-gold)] animate-bounce [animation-delay:300ms]" />
    </div>
  );
}

function CloseIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.5v15m7.5-7.5h-15" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
    </svg>
  );
}
