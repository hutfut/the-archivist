import { type DragEvent, useCallback, useRef, useState } from "react";

interface DocumentUploadProps {
  onUpload: (file: File) => Promise<void>;
  uploading: boolean;
}

export function DocumentUpload({ onUpload, uploading }: DocumentUploadProps) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) {
        onUpload(file);
      }
    },
    [onUpload],
  );

  const handleClick = useCallback(() => {
    inputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        onUpload(file);
      }
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    },
    [onUpload],
  );

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={handleClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") handleClick();
      }}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`
        flex flex-col items-center justify-center gap-2
        rounded-lg border-2 border-dashed p-6 mb-4
        cursor-pointer transition-colors
        ${dragOver
          ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30"
          : "border-gray-300 hover:border-gray-400 dark:border-gray-600 dark:hover:border-gray-500"
        }
        ${uploading ? "opacity-60 pointer-events-none" : ""}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt,.md"
        onChange={handleFileChange}
        className="hidden"
        aria-label="Upload document"
      />

      {uploading ? (
        <>
          <Spinner />
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Uploading &amp; processing...
          </span>
        </>
      ) : (
        <>
          <UploadIcon />
          <span className="text-sm text-gray-600 dark:text-gray-400">
            Drop a file here or <span className="text-blue-600 dark:text-blue-400 font-medium">browse</span>
          </span>
          <span className="text-xs text-gray-400 dark:text-gray-500">
            PDF, TXT, or Markdown
          </span>
        </>
      )}
    </div>
  );
}

function UploadIcon() {
  return (
    <svg
      className="w-8 h-8 text-gray-400"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.5}
        d="M12 16V4m0 0L8 8m4-4l4 4M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2"
      />
    </svg>
  );
}

function Spinner() {
  return (
    <svg
      className="w-6 h-6 animate-spin text-blue-500"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}
