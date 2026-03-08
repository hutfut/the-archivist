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
      className={`fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-40 w-14 h-14 rounded-full poe-btn-primary flex items-center justify-center shadow-lg transition-all duration-300 cursor-pointer ${
        open ? "" : "animate-glow-pulse"
      }`}
    >
      {open ? <CloseIcon /> : <TomeIcon />}
    </button>
  );
}

function TomeIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 2C9.5 2 7 3 5 4.5V20.5C7 19 9.5 18 12 18V2Z" opacity="0.9" />
      <path d="M12 2C14.5 2 17 3 19 4.5V20.5C17 19 14.5 18 12 18V2Z" opacity="0.7" />
      <line x1="12" y1="2" x2="12" y2="18" stroke="currentColor" strokeWidth="0.5" opacity="0.5" />
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
