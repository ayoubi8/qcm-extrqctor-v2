import { CheckCircle2 } from "lucide-react";
import type { ManualAutoRunNotice } from "./types";

interface AutoRunNotificationProps {
  notice: ManualAutoRunNotice | null;
}

export function AutoRunNotification({ notice }: AutoRunNotificationProps) {
  if (!notice) {
    return null;
  }
  const toneClass = {
    success: "border-emerald-400/50 bg-emerald-500/10 text-emerald-100",
    warning: "border-amber-400/50 bg-amber-500/10 text-amber-100",
    danger: "border-red-400/50 bg-red-500/10 text-red-100"
  }[notice.tone];

  return (
    <div className={`flex items-center gap-2 rounded-md border px-3 py-2 text-sm ${toneClass}`} role="status">
      <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
      <span>{notice.message}</span>
    </div>
  );
}
