import { useCallback, useEffect, useRef } from "react";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Delete",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (open && !dialog.open) {
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  const handleCancel = useCallback(() => {
    onCancel();
  }, [onCancel]);

  return (
    <dialog
      ref={dialogRef}
      onCancel={handleCancel}
      className="max-w-sm w-full rounded-xl p-0 backdrop:bg-black/60 bg-[var(--color-bg-secondary)] border border-[var(--color-border)] text-[var(--color-text-primary)] shadow-xl"
    >
      <div className="p-6">
        <h3 className="font-heading text-base font-semibold text-[var(--color-text-heading)] mb-2">{title}</h3>
        <p className="text-sm text-[var(--color-text-secondary)]">{message}</p>
      </div>
      <div className="flex justify-end gap-3 px-6 pb-6">
        <button
          type="button"
          onClick={onCancel}
          className="poe-btn-secondary text-sm"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={onConfirm}
          className="px-4 py-2 text-sm font-medium rounded-lg text-white bg-[var(--color-accent-crimson)] hover:bg-red-700 transition-colors cursor-pointer"
        >
          {confirmLabel}
        </button>
      </div>
    </dialog>
  );
}
