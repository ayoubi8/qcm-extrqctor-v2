import type { ReactNode } from "react";
import { StatusBadge } from "../ui";

interface ProjectShellProps {
  title: string;
  subtitle: string;
  status?: string;
  actions?: ReactNode;
  children: ReactNode;
}

export function ProjectShell({ title, subtitle, status = "draft", actions, children }: ProjectShellProps) {
  return (
    <section className="grid min-h-0 gap-4">
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-semibold text-slate-100">{title}</h1>
            <StatusBadge tone="info">{status}</StatusBadge>
          </div>
          <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
        </div>
        {actions}
      </header>
      {children}
    </section>
  );
}
