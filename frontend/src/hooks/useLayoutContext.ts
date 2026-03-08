import { useOutletContext } from "react-router-dom";
import type { UseChatReturn } from "./useChat";

interface UseDocumentsReturn {
  documents: { id: string; filename: string; content_type: string; file_size: number; chunk_count: number; created_at: string }[];
  loading: boolean;
  error: string | null;
  uploading: boolean;
  upload: (file: File) => Promise<void>;
  remove: (id: string) => Promise<void>;
  clearError: () => void;
}

export interface LayoutContext {
  documents: UseDocumentsReturn;
  chat: UseChatReturn;
  openChat: (prefill?: string) => void;
  openUpload: () => void;
}

export function useLayoutContext(): LayoutContext {
  return useOutletContext<LayoutContext>();
}
