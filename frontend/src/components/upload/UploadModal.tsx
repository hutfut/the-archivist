import { type DragEvent, useCallback, useEffect, useRef, useState } from "react";

interface UploadModalProps {
  open: boolean;
  onClose: () => void;
  onUpload: (file: File) => Promise<void>;
  uploading: boolean;
  error: string | null;
}

export function UploadModal({
  open,
  onClose,
  onUpload,
  uploading,
  error,
}: UploadModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    else if (!open && dialog.open) dialog.close();
  }, [open]);

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) onUpload(file);
    },
    [onUpload],
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onUpload(file);
      if (inputRef.current) inputRef.current.value = "";
    },
    [onUpload],
  );

  return (
    <dialog
      ref={dialogRef}
      onCancel={onClose}
      className="max-w-lg w-full rounded-xl p-0 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] shadow-2xl backdrop:bg-black/60"
    >
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-heading text-lg font-semibold text-[var(--color-accent-gold)]">
            Upload Document
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] cursor-pointer"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-md bg-[var(--color-accent-crimson-dim)]/30 text-sm text-red-300">
            {error}
          </div>
        )}

        <div
          role="button"
          tabIndex={0}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
          }}
          onDragOver={(e: DragEvent) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={(e: DragEvent) => { e.preventDefault(); setDragOver(false); }}
          onDrop={handleDrop}
          className={`flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-10 cursor-pointer transition-all ${
            dragOver
              ? "border-[var(--color-accent-gold)] bg-[var(--color-accent-gold)]/5"
              : "border-[var(--color-border)] hover:border-[var(--color-accent-gold-dim)]"
          } ${uploading ? "opacity-60 pointer-events-none" : ""}`}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.txt,.md"
            onChange={handleFileChange}
            className="hidden"
          />

          {uploading ? (
            <>
              <Spinner />
              <span className="text-sm text-[var(--color-text-secondary)]">
                Uploading &amp; processing...
              </span>
            </>
          ) : (
            <>
              <svg className="w-10 h-10 text-[var(--color-accent-gold-dim)]" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 16V4m0 0L8 8m4-4l4 4M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
              </svg>
              <div className="text-center">
                <span className="text-sm text-[var(--color-text-primary)]">
                  Drop a file here or{" "}
                  <span className="text-[var(--color-accent-gold)] font-medium">browse</span>
                </span>
                <p className="text-xs text-[var(--color-text-muted)] mt-1">
                  PDF, TXT, or Markdown &bull; Up to 50 MB
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </dialog>
  );
}

function Spinner() {
  return (
    <svg className="w-8 h-8 animate-spin text-[var(--color-accent-gold)]" fill="none" viewBox="0 0 24 24" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}
