import { useCallback, useEffect, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useChat } from "../../hooks/useChat";
import { useDocuments } from "../../hooks/useDocuments";
import { ChatDrawer } from "../chat/ChatDrawer";
import { UploadModal } from "../upload/UploadModal";
import { Footer } from "./Footer";
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

      <Footer />

      <FloatingChatButton open={chatOpen} onClick={toggleChat} />

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
