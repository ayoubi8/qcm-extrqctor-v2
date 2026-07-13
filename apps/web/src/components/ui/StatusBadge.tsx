type StatusTone = "neutral" | "success" | "warning" | "danger" | "info";

interface StatusBadgeProps {
  tone?: StatusTone;
  children: string;
}

const toneClass: Record<StatusTone, string> = {
  neutral: "border-slate-600 bg-slate-800 text-slate-200",
  success: "border-emerald-400/50 bg-emerald-500/10 text-emerald-200",
  warning: "border-amber-400/50 bg-amber-500/10 text-amber-200",
  danger: "border-red-400/50 bg-red-500/10 text-red-200",
  info: "border-cyan-400/50 bg-cyan-500/10 text-cyan-200"
};

export function StatusBadge({ tone = "neutral", children }: StatusBadgeProps) {
  return <span className={`inline-flex items-center rounded border px-2 py-1 text-xs font-medium ${toneClass[tone]}`}>{children}</span>;
}
