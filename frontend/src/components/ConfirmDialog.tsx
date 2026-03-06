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
      className="
        max-w-sm w-full rounded-xl p-0
        backdrop:bg-black/40
        bg-white dark:bg-gray-800
        text-gray-900 dark:text-gray-100
        shadow-xl
      "
    >
      <div className="p-6">
        <h3 className="text-base font-semibold mb-2">{title}</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">{message}</p>
      </div>
      <div className="flex justify-end gap-3 px-6 pb-6">
        <button
          type="button"
          onClick={onCancel}
          className="
            px-4 py-2 text-sm font-medium rounded-lg
            text-gray-700 dark:text-gray-300
            hover:bg-gray-100 dark:hover:bg-gray-700
            transition-colors cursor-pointer
          "
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={onConfirm}
          className="
            px-4 py-2 text-sm font-medium rounded-lg
            text-white bg-red-600 hover:bg-red-700
            transition-colors cursor-pointer
          "
        >
          {confirmLabel}
        </button>
      </div>
    </dialog>
  );
}
