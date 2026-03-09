import { useCallback, useEffect, useRef, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useChat } from "../../hooks/useChat";
import { useDocuments } from "../../hooks/useDocuments";
import { ChatDrawer } from "../chat/ChatDrawer";
import { UploadModal } from "../upload/UploadModal";
import { Header } from "./Header";

export function Layout() {
  const [chatOpen, setChatOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const chat = useChat();
  const docs = useDocuments();
  const navigate = useNavigate();
  const [chatPrefill, setChatPrefill] = useState<string | undefined>(undefined);
  const location = useLocation();

  useEffect(() => {
    if (!location.hash) {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  }, [location.pathname, location.hash]);

  const toggleChat = useCallback(() => {
    setChatOpen((prev) => !prev);
  }, []);

  const openChatWith = useCallback(
    (prefill?: string) => {
      setChatPrefill(prefill);
      setChatOpen(true);
    },
    [],
  );

  const handleUploadFromModal = useCallback(
    async (file: File) => {
      await docs.upload(file);
      setUploadOpen(false);
      navigate("/");
    },
    [docs, navigate],
  );

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <Header
        onUploadClick={() => setUploadOpen(true)}
      />

      <main className="flex-1 overflow-y-auto">
        <Outlet
          context={{
            documents: docs,
            chat,
            openChat: openChatWith,
            openUpload: () => setUploadOpen(true),
          }}
        />
      </main>

      <FloatingChatButton open={chatOpen} onClick={toggleChat} />

      <ChatCTABubble
        chatOpen={chatOpen}
        hasConversations={chat.conversations.length > 0}
        conversationsLoading={chat.loading}
        onOpen={() => setChatOpen(true)}
      />

      <ChatDrawer
        open={chatOpen}
        onClose={() => setChatOpen(false)}
        chat={chat}
        hasDocuments={docs.total > 0}
        prefill={chatPrefill}
        onPrefillConsumed={() => {
          setChatPrefill(undefined);
        }}
      />

      <UploadModal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onUpload={handleUploadFromModal}
        uploading={docs.uploading}
        error={docs.error}
      />
    </div>
  );
}

function FloatingChatButton({ open, onClick }: { open: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title="Ask The Caretaker"
      className={`fixed z-40 chat-btn-position w-16 h-16 rounded-full poe-btn-primary flex items-center justify-center shadow-lg transition-all duration-300 cursor-pointer ${
        open ? "" : "animate-glow-pulse"
      }`}
    >
      {open ? <CloseIcon /> : <TomeIcon />}
    </button>
  );
}

function TomeIcon() {
  return (
    <svg width="28" height="28" viewBox="2 0 32 32" fill="none" aria-hidden="true">
      <path
        d="M18 2C13 2 8 3.5 4 6V30C8 27.5 13 26 18 26V2Z"
        fill="var(--color-bg-primary)"
        opacity="0.9"
      />
      <path
        d="M18 2C23 2 28 3.5 32 6V30C28 27.5 23 26 18 26V2Z"
        fill="var(--color-bg-primary)"
        opacity="0.75"
      />
      <line x1="18" y1="2" x2="18" y2="26" stroke="var(--color-accent-crimson)" strokeWidth="1.5" />
      <line x1="7" y1="10" x2="15" y2="10" stroke="var(--color-bg-primary)" strokeWidth="0.8" opacity="0.5" />
      <line x1="7" y1="14" x2="14" y2="14" stroke="var(--color-bg-primary)" strokeWidth="0.8" opacity="0.5" />
      <line x1="7" y1="18" x2="15" y2="18" stroke="var(--color-bg-primary)" strokeWidth="0.8" opacity="0.5" />
      <line x1="21" y1="10" x2="29" y2="10" stroke="var(--color-bg-primary)" strokeWidth="0.8" opacity="0.5" />
      <line x1="21" y1="14" x2="28" y2="14" stroke="var(--color-bg-primary)" strokeWidth="0.8" opacity="0.5" />
      <line x1="21" y1="18" x2="29" y2="18" stroke="var(--color-bg-primary)" strokeWidth="0.8" opacity="0.5" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

const CTA_MESSAGES = [
  "Ask The Caretaker about your documents\u2026",
  "Need help finding something in The Archive?",
  "Chat with The Caretaker about anything here\u2026",
  "Curious about connections between documents?",
];

const CTA_INITIAL_DELAY_MS = 45_000;
const CTA_REPEAT_INTERVAL_MS = 300_000;
const CTA_TYPING_SPEED_MS = 35;
const CTA_DISPLAY_DURATION_MS = 4_000;
const CTA_FADE_DURATION_MS = 500;

type CTAPhase = "hidden" | "typing" | "showing" | "fading";

function ChatCTABubble({
  chatOpen,
  hasConversations,
  conversationsLoading,
  onOpen,
}: {
  chatOpen: boolean;
  hasConversations: boolean;
  conversationsLoading: boolean;
  onOpen: () => void;
}) {
  const [phase, setPhase] = useState<CTAPhase>("hidden");
  const [typedText, setTypedText] = useState("");

  const msgIdxRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const shouldShow = !hasConversations && !conversationsLoading && !chatOpen;

  const cleanup = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const startTypingRef = useRef<() => void>(() => {});
  startTypingRef.current = () => {
    const msg = CTA_MESSAGES[msgIdxRef.current % CTA_MESSAGES.length];
    let charIdx = 0;
    setTypedText("");
    setPhase("typing");

    intervalRef.current = setInterval(() => {
      charIdx++;
      setTypedText(msg.slice(0, charIdx));

      if (charIdx >= msg.length) {
        if (intervalRef.current !== null) clearInterval(intervalRef.current);
        intervalRef.current = null;
        setPhase("showing");

        timerRef.current = setTimeout(() => {
          setPhase("fading");
          timerRef.current = setTimeout(() => {
            setPhase("hidden");
            msgIdxRef.current = (msgIdxRef.current + 1) % CTA_MESSAGES.length;
            timerRef.current = setTimeout(
              () => startTypingRef.current(),
              CTA_REPEAT_INTERVAL_MS,
            );
          }, CTA_FADE_DURATION_MS);
        }, CTA_DISPLAY_DURATION_MS);
      }
    }, CTA_TYPING_SPEED_MS);
  };

  useEffect(() => {
    if (!shouldShow) {
      cleanup();
      setPhase("hidden");
      return;
    }

    timerRef.current = setTimeout(
      () => startTypingRef.current(),
      CTA_INITIAL_DELAY_MS,
    );

    return cleanup;
  }, [shouldShow, cleanup]);

  if (phase === "hidden") return null;

  return (
    <button
      type="button"
      onClick={onOpen}
      className={`fixed z-40 chat-cta-position chat-cta-bubble max-w-60 px-4 py-3 rounded-lg bg-[var(--color-bg-elevated)] border border-[var(--color-border-gold)] shadow-lg cursor-pointer transition-opacity duration-500 ${
        phase === "fading" ? "opacity-0" : "opacity-100"
      }`}
    >
      <span className="text-sm text-[var(--color-text-primary)]">
        {typedText}
        {phase === "typing" && (
          <span className="animate-blink-cursor text-[var(--color-accent-gold)]">
            |
          </span>
        )}
      </span>
    </button>
  );
}
