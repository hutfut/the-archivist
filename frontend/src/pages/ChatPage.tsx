import { useEffect } from "react";
import { useLayoutContext } from "../hooks/useLayoutContext";
import { CaretakerAvatar } from "../components/chat/avatars";

export function ChatPage() {
  const { openChat } = useLayoutContext();

  useEffect(() => {
    openChat();
  }, [openChat]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-6">
      <div className="mb-6">
        <CaretakerAvatar size="lg" />
      </div>
      <h1 className="font-heading text-2xl font-semibold text-[var(--color-accent-gold)] mb-3">
        The Caretaker
      </h1>
      <p className="text-[var(--color-text-secondary)] max-w-md">
        The chat drawer has been opened. Ask questions about your uploaded documents
        and The Caretaker will provide answers with source citations.
      </p>
    </div>
  );
}
