import { useState } from "react";
import type { DocumentResponse } from "../api/documents.ts";
import { ConfirmDialog } from "./ConfirmDialog.tsx";

interface DocumentListProps {
  documents: DocumentResponse[];
  onDelete: (id: string) => Promise<void>;
}

export function DocumentList({ documents, onDelete }: DocumentListProps) {
  const [pendingDelete, setPendingDelete] = useState<DocumentResponse | null>(null);
  const [deleting, setDeleting] = useState(false);

  const handleConfirmDelete = async () => {
    if (!pendingDelete) return;
    try {
      setDeleting(true);
      await onDelete(pendingDelete.id);
    } finally {
      setDeleting(false);
      setPendingDelete(null);
    }
  };

  return (
    <>
      {documents.length === 0 ? (
        <p className="text-sm text-gray-400 dark:text-gray-500 text-center py-8">
          No documents uploaded yet.
          <br />
          Upload a document to get started.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {documents.map((doc) => (
            <DocumentItem
              key={doc.id}
              document={doc}
              onDeleteClick={() => setPendingDelete(doc)}
            />
          ))}
        </ul>
      )}

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete document"
        message={
          pendingDelete
            ? `Delete "${pendingDelete.filename}"? This will remove the document and all its processed data. This cannot be undone.`
            : ""
        }
        confirmLabel={deleting ? "Deleting..." : "Delete"}
        onConfirm={handleConfirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </>
  );
}

interface DocumentItemProps {
  document: DocumentResponse;
  onDeleteClick: () => void;
}

function DocumentItem({ document, onDeleteClick }: DocumentItemProps) {
  return (
    <li className="flex items-start gap-3 p-3 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
      <FileIcon contentType={document.content_type} />

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate" title={document.filename}>
          {document.filename}
        </p>
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1 text-xs text-gray-500 dark:text-gray-400">
          <span>{formatFileSize(document.file_size)}</span>
          <span>{document.chunk_count} chunk{document.chunk_count !== 1 ? "s" : ""}</span>
          <span>{formatDate(document.created_at)}</span>
        </div>
      </div>

      <button
        type="button"
        onClick={onDeleteClick}
        title="Delete document"
        className="
          p-1.5 rounded-md text-gray-400 hover:text-red-600
          hover:bg-red-50 dark:hover:bg-red-950/30
          transition-colors shrink-0 cursor-pointer
        "
      >
        <TrashIcon />
      </button>
    </li>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** i;
  return `${i === 0 ? value : value.toFixed(1)} ${units[i]}`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

const FILE_TYPE_ICONS: Record<string, string> = {
  "application/pdf": "PDF",
  "text/plain": "TXT",
  "text/markdown": "MD",
};

function FileIcon({ contentType }: { contentType: string }) {
  const label = FILE_TYPE_ICONS[contentType] ?? "DOC";
  return (
    <div className="
      flex items-center justify-center w-10 h-10 rounded-lg shrink-0
      bg-gray-100 dark:bg-gray-700
      text-xs font-bold text-gray-500 dark:text-gray-400
    ">
      {label}
    </div>
  );
}

function TrashIcon() {
  return (
    <svg
      className="w-4 h-4"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
      />
    </svg>
  );
}
