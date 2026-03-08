import { useEffect } from "react";
import { useLayoutContext } from "../hooks/useLayoutContext";

export function ChatPage() {
  const { openChat } = useLayoutContext();

  useEffect(() => {
    openChat();
  }, [openChat]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-6">
      <div className="w-20 h-20 mb-6 rounded-full bg-gradient-to-br from-[var(--color-accent-gold)]/20 to-[var(--color-accent-crimson)]/10 border border-[var(--color-border-gold)] flex items-center justify-center">
        <span className="text-3xl font-heading text-[var(--color-accent-gold)]">A</span>
      </div>
      <h1 className="font-heading text-2xl font-semibold text-[var(--color-accent-gold)] mb-3">
        The Archivist
      </h1>
      <p className="text-[var(--color-text-secondary)] max-w-md">
        The chat drawer has been opened. Ask questions about your uploaded documents
        and The Archivist will provide answers with source citations.
      </p>
    </div>
  );
}
