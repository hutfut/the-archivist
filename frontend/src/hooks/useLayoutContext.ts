import { useOutletContext } from "react-router-dom";
import type { UseChatReturn } from "./useChat";
import type { UseDocumentsReturn } from "./useDocuments";

export interface LayoutContext {
  documents: UseDocumentsReturn;
  chat: UseChatReturn;
  openChat: (prefill?: string) => void;
  openUpload: () => void;
}

export function useLayoutContext(): LayoutContext {
  return useOutletContext<LayoutContext>();
}
