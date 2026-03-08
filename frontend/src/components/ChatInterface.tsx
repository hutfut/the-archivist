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
import type { ConversationResponse, MessageResponse, SourceAttribution } from "../api/conversations.ts";
import type { StreamingMessage, UseChatReturn } from "../hooks/useChat.ts";
import { toSlug } from "../lib/utils.ts";
import { ConfirmDialog } from "./ConfirmDialog.tsx";

type ChatProps = UseChatReturn;

export function ChatInterface(props: ChatProps) {
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
  } = props;

  return (
    <div className="flex flex-col h-full">
      <ConversationSelector
        conversations={conversations}
        activeId={activeConversationId}
        onSelect={selectConversation}
        onCreate={createChat}
        onDelete={deleteChat}
      />

      {error && (
        <div className="flex items-start gap-2 mx-4 mb-2 p-3 rounded-lg bg-red-50 dark:bg-red-950/30 text-sm text-red-700 dark:text-red-400">
          <span className="flex-1">{error}</span>
          <button
            type="button"
            onClick={clearError}
            className="shrink-0 text-red-400 hover:text-red-600 cursor-pointer"
            aria-label="Dismiss error"
          >
            &times;
          </button>
        </div>
      )}

      {activeConversationId ? (
        <>
          <MessageList messages={messages} streaming={streaming} />
          <MessageInput onSend={sendMessage} disabled={sending} />
        </>
      ) : (
        <EmptyState onCreate={createChat} />
      )}
    </div>
  );
}

function ConversationSelector({
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
  const [confirmDelete, setConfirmDelete] = useState(false);

  const handleDelete = async () => {
    if (activeId) {
      await onDelete(activeId);
      setConfirmDelete(false);
    }
  };

  return (
    <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-200 dark:border-gray-700 shrink-0">
      <select
        value={activeId ?? ""}
        onChange={(e) => {
          if (e.target.value) onSelect(e.target.value);
        }}
        className="
          flex-1 min-w-0 px-3 py-2 text-sm rounded-lg
          border border-gray-300 dark:border-gray-600
          bg-white dark:bg-gray-700
          text-gray-900 dark:text-gray-100
          focus:outline-none focus:ring-2 focus:ring-blue-500
          truncate
        "
      >
        {conversations.length === 0 && (
          <option value="">No conversations</option>
        )}
        {conversations.map((c) => (
          <option key={c.id} value={c.id}>
            {c.title ?? "New conversation"}
          </option>
        ))}
      </select>

      <button
        type="button"
        onClick={onCreate}
        title="New conversation"
        className="
          shrink-0 p-2 rounded-lg text-sm font-medium
          text-gray-600 dark:text-gray-300
          hover:bg-gray-100 dark:hover:bg-gray-700
          transition-colors cursor-pointer
        "
      >
        <PlusIcon />
      </button>

      {activeId && (
        <button
          type="button"
          onClick={() => setConfirmDelete(true)}
          title="Delete conversation"
          className="
            shrink-0 p-2 rounded-lg text-sm
            text-gray-400 hover:text-red-600
            hover:bg-red-50 dark:hover:bg-red-950/30
            transition-colors cursor-pointer
          "
        >
          <TrashIcon />
        </button>
      )}

      <ConfirmDialog
        open={confirmDelete}
        title="Delete conversation"
        message="Delete this conversation and all its messages? This cannot be undone."
        confirmLabel="Delete"
        onConfirm={handleDelete}
        onCancel={() => setConfirmDelete(false)}
      />
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
      <div className="flex-1 flex items-center justify-center text-gray-400 dark:text-gray-500 text-sm px-4">
        Send a message to start the conversation.
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}

      {streaming && (
        <div className="flex justify-start">
          <div className="max-w-[80%] rounded-2xl px-4 py-3 bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100">
            {streaming.content ? (
              <div className="prose prose-sm dark:prose-invert max-w-none">
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
        className={`
          max-w-[80%] rounded-2xl px-4 py-3
          ${
            isUser
              ? "bg-blue-600 text-white"
              : "bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          }
        `}
      >
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none">
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
  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600">
      <button
        type="button"
        onClick={() => setExpanded(expanded !== null ? null : 0)}
        className="text-xs font-medium text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 cursor-pointer"
      >
        Sources ({sources.length})
      </button>

      {expanded !== null && (
        <ul className="mt-2 space-y-2">
          {sources.map((source, i) => (
            <SourceItem
              key={`${source.document_id}-${i}`}
              source={source}
              isExpanded={expanded === i}
              onToggle={() => setExpanded(expanded === i ? null : i)}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function SourceItem({
  source,
  isExpanded,
  onToggle,
}: {
  source: SourceAttribution;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  return (
    <li>
      <div className="flex items-baseline gap-1 text-xs">
        <Link
          to={`/doc/${toSlug(source.document_id, source.filename)}`}
          className="font-medium text-blue-600 dark:text-blue-400 hover:underline"
        >
          {source.section_heading
            ? `${source.filename} > ${source.section_heading}`
            : source.filename}
        </Link>
        <span className="text-gray-400 dark:text-gray-500">
          ({(source.similarity_score * 100).toFixed(0)}%)
        </span>
        <button
          type="button"
          onClick={onToggle}
          className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 cursor-pointer ml-1"
        >
          {isExpanded ? "less" : "more"}
        </button>
      </div>
      {isExpanded && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 whitespace-pre-wrap">
          {source.chunk_content}
        </p>
      )}
    </li>
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
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
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
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="shrink-0 flex items-end gap-2 px-4 py-3 border-t border-gray-200 dark:border-gray-700"
    >
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        placeholder="Ask a question about your documents..."
        disabled={disabled}
        rows={1}
        className="
          flex-1 resize-none px-4 py-2.5 text-sm rounded-xl
          border border-gray-300 dark:border-gray-600
          bg-white dark:bg-gray-700
          text-gray-900 dark:text-gray-100
          placeholder-gray-400
          focus:outline-none focus:ring-2 focus:ring-blue-500
          disabled:opacity-50
        "
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="
          shrink-0 p-2.5 rounded-xl
          bg-blue-600 text-white
          hover:bg-blue-700
          disabled:opacity-40 disabled:cursor-not-allowed
          transition-colors cursor-pointer
        "
        title="Send message"
      >
        <SendIcon />
      </button>
    </form>
  );
}

function EmptyState({ onCreate }: { onCreate: () => Promise<void> }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center px-6 gap-4">
      <div className="w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
        <ChatBubbleIcon />
      </div>
      <div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Start a conversation
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Ask questions about your uploaded documents.
        </p>
      </div>
      <button
        type="button"
        onClick={onCreate}
        className="
          px-4 py-2 text-sm font-medium rounded-lg
          bg-blue-600 text-white hover:bg-blue-700
          transition-colors cursor-pointer
        "
      >
        New conversation
      </button>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-1 py-1" aria-label="Assistant is typing">
      <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce [animation-delay:0ms]" />
      <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce [animation-delay:150ms]" />
      <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce [animation-delay:300ms]" />
    </div>
  );
}

function PlusIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4.5v15m7.5-7.5h-15" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
      />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
      />
    </svg>
  );
}

function ChatBubbleIcon() {
  return (
    <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zM3.75 20.25V4.125C3.75 3.504 4.254 3 4.875 3h14.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125H7.875L3.75 20.25z"
      />
    </svg>
  );
}
