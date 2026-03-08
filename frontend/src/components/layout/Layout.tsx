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
        onToggleChat={toggleChat}
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

      <ChatDrawer
        open={chatOpen}
        onClose={() => setChatOpen(false)}
        chat={chat}
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
