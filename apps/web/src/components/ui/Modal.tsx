import { X } from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "./Button";

interface ModalProps {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
}

export function Modal({ open, title, children, onClose }: ModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/80 p-4" role="presentation">
      <section
        className="w-full max-w-lg rounded-lg border border-slate-700 bg-slate-900 shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <header className="flex min-h-14 items-center justify-between gap-3 border-b border-slate-800 px-4">
          <h2 id="modal-title" className="text-base font-semibold">
            {title}
          </h2>
          <Button variant="ghost" icon={<X className="h-4 w-4" aria-hidden="true" />} onClick={onClose} aria-label="Close modal">
            Close
          </Button>
        </header>
        <div className="p-4">{children}</div>
      </section>
    </div>
  );
}
