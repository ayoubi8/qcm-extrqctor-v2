import { ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";

interface AuthShellProps {
  title: string;
  tone?: "info" | "warning";
  children: ReactNode;
}

export function AuthShell({ title, tone = "info", children }: AuthShellProps) {
  const iconClass = tone === "warning" ? "text-amber-300" : "text-cyan-300";
  const borderClass = tone === "warning" ? "border-amber-500/40" : "border-slate-800";

  return (
    <main className="grid min-h-screen place-items-center bg-slate-950 px-6 text-slate-100">
      <section className={`w-full max-w-sm rounded-lg border ${borderClass} bg-slate-900 p-5`}>
        <ShieldCheck className={`mb-4 h-6 w-6 ${iconClass}`} aria-hidden="true" />
        <h1 className="text-xl font-semibold">{title}</h1>
        <div className="mt-2 text-sm text-slate-400">{children}</div>
      </section>
    </main>
  );
}
