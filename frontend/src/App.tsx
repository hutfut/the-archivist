import { ChatInterface } from "./components/ChatInterface.tsx";
import { DocumentList } from "./components/DocumentList.tsx";
import { DocumentUpload } from "./components/DocumentUpload.tsx";
import { useChat } from "./hooks/useChat.ts";
import { useDocuments } from "./hooks/useDocuments.ts";

function App() {
  const { documents, loading, error, uploading, upload, remove, clearError } =
    useDocuments();
  const chat = useChat();

  return (
    <div className="grid grid-cols-[320px_1fr] h-screen overflow-hidden">
      <aside className="flex flex-col p-6 overflow-y-auto border-r border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900">
        <h2 className="text-lg font-semibold mb-3">Documents</h2>

        <DocumentUpload onUpload={upload} uploading={uploading} />

        {error && (
          <div className="flex items-start gap-2 mb-3 p-3 rounded-lg bg-red-50 dark:bg-red-950/30 text-sm text-red-700 dark:text-red-400">
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

        {loading ? (
          <p className="text-sm text-gray-400 text-center py-8">
            Loading documents...
          </p>
        ) : (
          <DocumentList documents={documents} onDelete={remove} />
        )}
      </aside>

      <main className="flex flex-col overflow-hidden bg-white dark:bg-gray-800">
        <ChatInterface {...chat} />
      </main>
    </div>
  );
}

export default App
